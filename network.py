import socket
import select
import threading
import struct
import pickle

def connect(hostname, port):
    print('connect', hostname, port)
    return Network(socket.create_connection((hostname, port)))

def serve(port):
    print('serve', port)
    s = socket.create_server(('', port), family=socket.AF_INET6, dualstack_ipv6=True)
    return Network(s, True)


class Match:
    def __init__(self, start, end, offset):
        self.start = start
        self.end = end
        self.offset = offset

    def overlaps(self, m):
        return not (self.start >= m.end or self.end <= m.start)

    def contains(self, p):
        return not (self.start > p or self.end <= p)

    def getLength(self):
        return self.end - self.start

    def getEndOffset(self):
        return self.offset + self.getLength()


class MatchFinder:
    def __init__(self, buf):
        self.buf = buf
        self.matches = []

    def __findFirstMatch(self, buf, start0, start1, minLen):

        # state of growing match
        mStart = start1 - 1 # init because read when first char not matching, in      buf
        #mEnd = 0           # inits later                                   , in      buf
        #mOffset = 0        # inits later                                   , in self.buf
        mLen = 0            # 0 means no match yet

        # i0 means in old buf (=self.buf)
        # i1 means in new buf (=     buf)
        i0 = start0 - 1
        i1 = start1 - 1
        n0 = len(self.buf)
        n1 = len(buf)
        while i0+1 < n0 and i1+1 < n1:

            # move through both buffers while they match
            i0 += 1
            i1 += 1

            if self.buf[i0] == buf[i1]: # char matches?
                if mLen == 0:           # prev chars didn't match yet?

                    # start new growing match from here
                    mStart = i1
                    mEnd = i1
                    mOffset = i0
                    mLen = 1

                else:                   # prev chars matched already?

                    # grow growing match
                    mEnd += 1
                    mLen += 1

            else:                       # char matches not?

                if mLen >= minLen:      # match grown until here is good-enough result?

                    # return good-enought result
                    return Match(mStart, mEnd+1, mOffset)

                else:                   # match grown until here is not good enough?

                    # start new growing match attempt
                    mLen = 0
                    mStart += 1 # causes start 1 char to the right (using i1) if this new attempt fails too
                    i0 = start0       - 1
                    i1 = mStart # + 1 - 1

        if mLen >= minLen: # match grown up until buf end is good-enough result?

            # return good-enought result
            return Match(mStart, mEnd+1, mOffset)

        return None

    def addMatchesKindaFast(self, buf):

        MATCH_LEN_MIN = 3 # ---------------------------------------------------------------- tweak
        MATCH_LEN_BETTER = 8 # ---------------------------------------------------------------- tweak

        i0 = -1
        n0 = len(self.buf)
        while i0+1 < n0:
            i0 += 1
            match = self.__findFirstMatch(buf, i0, i0, MATCH_LEN_MIN) # ---------------------------------------------------------------- tweak
            matchBetter = None
            if match is not None:
                if match.end-match.start < MATCH_LEN_BETTER:
                    matchBetter = self.__findFirstMatch(buf, i0, match.start+1, MATCH_LEN_BETTER) # ---------------------------------------------------------------- tweak
 
            if matchBetter is not None:
                self.addMatch(matchBetter)
                i0 += matchBetter.end-1 - matchBetter.start
            elif match is not None:
                self.addMatch(match)
                i0 += match.end-1 - match.start

    def addMatchesFast(self, buf):

        MATCH_LEN_MIN = 3 # ---------------------------------------------------------------- tweak

        i0 = -1
        n0 = len(self.buf)
        while i0+1 < n0:
            i0 += 1
            match = self.__findFirstMatch(buf, i0, i0, MATCH_LEN_MIN) # ---------------------------------------------------------------- tweak

            if match is not None:
                self.addMatch(match)
                i0 += match.end-1 - match.start

    def addMatches(self, buf):
        windowSize = 20

        windowStart = 0
        windowEnd = min(windowSize, len(self.buf))

        for i in range(len(buf)):
            if len(self.matches) > 0 and not self.matches[-1].contains(i):
                matchEnd = self.matches[-1].getEndOffset()

                windowStart = max(matchEnd - windowSize, 0)
                windowEnd = min(matchEnd + windowSize, len(self.buf))

            for j in range(windowStart, windowEnd):
                j = self.buf.find(buf[i], j, windowEnd)
                if j == -1:
                    break

                k = 1
                while i + k < len(buf) and j + k < len(self.buf):
                    if buf[i + k] != self.buf[j + k]:
                        break
                    k += 1

                if k >= 3:
                    self.addMatch(Match(i, i + k, j))

    def addMatch(self, match):
        if len(self.matches) > 0 and self.matches[-1].overlaps(match):
            if match.getLength() <= self.matches[-1].getLength():
                return False

            self.matches[-1] = match
            return True

        self.matches.append(match)
        return True


class OffsetPair:
    def __init__(self, a, b):
        self.a = a
        self.b = b

    def write(self, v):
        if v < 0xf:
            return []

        out = []
        c = 0

        while v >= 0xff << (c * 8):
            out.append(0xff)

            if c == 3:
                out.append(0)
                break

            c += 1

        i = c
        while i >= 0:
            out.append((v >> (i * 8)) & 0xff)
            i -= 1

        return out

    def encode(self):
        first = self.a << 4 if self.a < 0xf else 0xf0
        first |= self.b if self.b < 0xf else 0xf

        return bytes([first] + self.write(self.a) + self.write(self.b))


class PacketCompressor:
    def __init__(self):
        self.lastPacket = None

    def compress(self, packet):
        if self.lastPacket is None:
            self.lastPacket = packet
            return packet

        finder = MatchFinder(self.lastPacket)
        finder.addMatchesFast(packet)

        readPos = 0
        writePos = 0
        out = b''

        for m in finder.matches:
            #print('match(start1,end1,offset0):', m.start, m.end, m.offset)
            if writePos < m.start:
                matchLength = m.start - writePos
                out += OffsetPair(matchLength - 1, 0).encode()
                out += packet[writePos:writePos + matchLength]
                writePos = m.start

            matchOffset = m.offset - readPos
            if matchOffset < 0:
                matchOffset = 127 - matchOffset

            out += OffsetPair(matchOffset, m.getLength() - 2).encode()
            readPos = m.offset + m.getLength()
            writePos += m.getLength()

        if writePos < len(packet):
            matchLength = len(packet) - writePos
            out += OffsetPair(matchLength - 1, 0).encode()
            out += packet[writePos:writePos + matchLength]

        self.lastPacket = packet
        return out


if 0:
    import time
    def testPacketCompressor(data0, data1):
        MAX_DATA_PRINT_LEN = 30
        print('')
        if len(data0) > MAX_DATA_PRINT_LEN:
            print('data0: len=',len(data0), ' data=', 'b\'...\'', sep='')
        else:
            print('data0: len=',len(data0), ' data=', data0, sep='')
        if len(data1) > MAX_DATA_PRINT_LEN:
            print('data1: len=',len(data1), ' data=', 'b\'...\'', sep='')
        else:
            print('data1: len=',len(data1), ' data=', data1, sep='')
        pc = PacketCompressor()
        pc.compress(data0)
        start = time.time()

        #TEST_COMPRESSIONS = 300
        #print('compressed',TEST_COMPRESSIONS*2,'times')
        #for i in range(TEST_COMPRESSIONS):
        #    dataCompressed = pc.compress(data1)
        #    dataCompressed = pc.compress(data0)
        print('compressed 1 time')
        dataCompressed = pc.compress(data1)

        if len(dataCompressed) > MAX_DATA_PRINT_LEN:
            print('dataCompressed: len=',len(dataCompressed), ' data=', 'b\'...\'', sep='')
        else:
            print('dataCompressed: len=',len(dataCompressed), ' data=', dataCompressed, sep='')
        print('compressed to', round(100*len(dataCompressed)/len(data0)), '%')
        print('time', (time.time() - start) * 1000, 'ms')


    # example: real data
    data0=b'\x80\x04\x95:\x05\x00\x00\x00\x00\x00\x00\x8c\tgamestate\x94\x8c\tGameState\x94\x93\x94)\x81\x94}\x94(\x8c\x07objects\x94}\x94(J\xff\xff\xff\xff\x8c\x0cplayerobject\x94\x8c\x06Player\x94\x93\x94)\x81\x94}\x94(\x8c\x01x\x94G@7\x00\x00\x00\x00\x00\x00\x8c\x01y\x94G@R\x80\x00\x00\x00\x00\x00\x8c\x04tile\x94\x8c\x011\x94\x8c\x04xdir\x94K\x00\x8c\x04ydir\x94K\x00\x8c\x07facedir\x94K\x00\x8c\x05speed\x94K\x01\x8c\x05width\x94K\x08\x8c\x06height\x94K\x08\x8c\x08playerid\x94K\x00\x8c\nplayertile\x94K\x01\x8c\x04tick\x94M\x94\x0b\x8c\x04anim\x94K\x00\x8c\nis_walking\x94\x89\x8c\x06status\x94\x8c\x05ALIVE\x94\x8c\ndeath_time\x94K\x00\x8c\rtime_to_alive\x94K\x02\x8c\x05old_x\x94G@7\x00\x00\x00\x00\x00\x00\x8c\x05old_y\x94G@R\x80\x00\x00\x00\x00\x00\x8c\tkick_mode\x94\x89\x8c\nkick_angle\x94K\x00K\x00\x86\x94ubJ\xfe\xff\xff\xff\x8c\x04ball\x94\x8c\x04Ball\x94\x93\x94)\x81\x94}\x94(h\x0cG@U\x90\xfd\xaaY\xeb\xech\rG@[`\x85\x82\x14aPh\x0e\x8c\x01o\x94h\x10G\x00\x00\x00\x00\x00\x00\x00\x00h\x11G\x00\x00\x00\x00\x00\x00\x00\x00h\x12K\x00h\x13K\x01h\x14K\x05h\x15K\x04\x8c\x01z\x94K\x00\x8c\x04zdir\x94G\x00\x00\x00\x00\x00\x00\x00\x00ubJ\xfd\xff\xff\xff\x8c\x04bird\x94\x8c\x04Bird\x94\x93\x94)\x81\x94}\x94(\x8c\tSPEED_DIV\x94K\x10\x8c\x1bSPEED_COLLISION_MULT_GROUND\x94KP\x8c\x0bWALL_HEIGHT\x94K\x0ch\x0cG@g \x00\x00\x00\x00\x00h\rG@_\xe0\x00\x00\x00\x00\x00h\x0e\x8c\x01v\x94h\x10J\xf6\xff\xff\xffh\x11K\nh\x12K\x00h\x13K\x01h\x14K\x06h\x15K\x02h*K\x00\x8c\x04size\x94K\x08h+K\x0fubJ\xebe\x0b\x00\x8c\x04worm\x94\x8c\x04Worm\x94\x93\x94)\x81\x94}\x94(h\x0cK\x13h\rK\th\x0eNh\x10J\xff\xff\xff\xffh\x11K\x00h\x12K\x00h\x13K\x01h\x14K\x08h\x15K\x08\x8c\x04head\x94]\x94(K\x13K\te\x8c\x04body\x94]\x94(]\x94(K\x14K\te]\x94(K\x15K\te]\x94(K\x16K\te]\x94(K\x16K\x08e]\x94(K\x16K\x07e]\x94(K\x16K\x06e]\x94(K\x15K\x06e]\x94(K\x14K\x06e]\x94(K\x13K\x06e]\x94(K\x12K\x06e]\x94(K\x11K\x06e]\x94(K\x10K\x06e]\x94(K\x10K\x06e]\x94(K\x0fK\x06e]\x94(K\x0fK\x06e]\x94(K\x0eK\x06ee\x8c\x05tiles\x94]\x94(\x8c\x01H\x94\x8c\x01B\x94e\x8c\x0elast_move_time\x94GA\xd8.=I\r\xaf\x19\x8c\tmove_time\x94G?\xc9\x99\x99\x99\x99\x99\x9a\x8c\x13steps_till_addition\x94K\x01\x8c\x0cstep_counter\x94K\x0c\x8c\x08move_dir\x94]\x94(K\x00K\x00e\x8c\tdebugList\x94]\x94\x8c\n_MOVEMENTS\x94]\x94(]\x94(J\xff\xff\xff\xffK\x00e]\x94(K\x01K\x00e]\x94(K\x00J\xff\xff\xff\xffe]\x94(K\x00K\x01ee\x8c\x08_dir_ops\x94]\x94(K\x02K\x01K\x04K\x03e\x8c\x05state\x94h\x1c\x8c\rtime_of_death\x94GA\xd8.=Fz7\n\x8c\x0ftime_to_respawn\x94G?\xf8\x00\x00\x00\x00\x00\x00\x8c\x0cgrow_counter\x94K\x00ubJ\x99\xe1\x07\x00h\t)\x81\x94}\x94(h\x0cG@T`\x00\x00\x00\x00\x00h\rG@Z\xa0\x00\x00\x00\x00\x00h\x0e\x8c\x012\x94h\x10K\x00h\x11K\x01h\x12K\x00h\x13K\x01h\x14K\x08h\x15K\x08h\x16K\x01h\x17K\x02h\x18M\xc7\x05h\x19K\x02h\x1a\x88h\x1bh\x1ch\x1dK\x00h\x1eK\x02h\x1fG@T`\x00\x00\x00\x00\x00h G@Z\x80\x00\x00\x00\x00\x00h!\x88h"G?\xef\xff\xf9xs\xee\x02G?dq8.3U\xd2\x86\x94ubu\x8c\tlevelname\x94\x8c\x04LEV3\x94\x8c\x06points\x94K\x00ub.'
    data1=b'\x80\x04\x95:\x05\x00\x00\x00\x00\x00\x00\x8c\tgamestate\x94\x8c\tGameState\x94\x93\x94)\x81\x94}\x94(\x8c\x07objects\x94}\x94(J\xff\xff\xff\xff\x8c\x0cplayerobject\x94\x8c\x06Player\x94\x93\x94)\x81\x94}\x94(\x8c\x01x\x94G@7\x00\x00\x00\x00\x00\x00\x8c\x01y\x94G@S@\x00\x00\x00\x00\x00\x8c\x04tile\x94\x8c\x011\x94\x8c\x04xdir\x94K\x00\x8c\x04ydir\x94K\x01\x8c\x07facedir\x94K\x00\x8c\x05speed\x94K\x01\x8c\x05width\x94K\x08\x8c\x06height\x94K\x08\x8c\x08playerid\x94K\x00\x8c\nplayertile\x94K\x01\x8c\x04tick\x94M\x98\x0b\x8c\x04anim\x94K\x01\x8c\nis_walking\x94\x88\x8c\x06status\x94\x8c\x05ALIVE\x94\x8c\ndeath_time\x94K\x00\x8c\rtime_to_alive\x94K\x02\x8c\x05old_x\x94G@7\x00\x00\x00\x00\x00\x00\x8c\x05old_y\x94G@S\x00\x00\x00\x00\x00\x00\x8c\tkick_mode\x94\x89\x8c\nkick_angle\x94K\x00K\x00\x86\x94ubJ\xfe\xff\xff\xff\x8c\x04ball\x94\x8c\x04Ball\x94\x93\x94)\x81\x94}\x94(h\x0cG@U\x90\xfd\xaaY\xeb\xech\rG@[`\x85\x82\x14aPh\x0e\x8c\x01o\x94h\x10G\x00\x00\x00\x00\x00\x00\x00\x00h\x11G\x00\x00\x00\x00\x00\x00\x00\x00h\x12K\x00h\x13K\x01h\x14K\x05h\x15K\x04\x8c\x01z\x94K\x00\x8c\x04zdir\x94G\x00\x00\x00\x00\x00\x00\x00\x00ubJ\xfd\xff\xff\xff\x8c\x04bird\x94\x8c\x04Bird\x94\x93\x94)\x81\x94}\x94(\x8c\tSPEED_DIV\x94K\x10\x8c\x1bSPEED_COLLISION_MULT_GROUND\x94KP\x8c\x0bWALL_HEIGHT\x94K\x0ch\x0cG@f\xd0\x00\x00\x00\x00\x00h\rG@`@\x00\x00\x00\x00\x00h\x0e\x8c\x01v\x94h\x10J\xf6\xff\xff\xffh\x11K\nh\x12K\x00h\x13K\x01h\x14K\x06h\x15K\x02h*K\x00\x8c\x04size\x94K\x08h+K\x0fubJ\xebe\x0b\x00\x8c\x04worm\x94\x8c\x04Worm\x94\x93\x94)\x81\x94}\x94(h\x0cK\x12h\rK\th\x0eNh\x10J\xff\xff\xff\xffh\x11K\x00h\x12K\x00h\x13K\x01h\x14K\x08h\x15K\x08\x8c\x04head\x94]\x94(K\x12K\te\x8c\x04body\x94]\x94(]\x94(K\x13K\te]\x94(K\x14K\te]\x94(K\x15K\te]\x94(K\x16K\te]\x94(K\x16K\x08e]\x94(K\x16K\x07e]\x94(K\x16K\x06e]\x94(K\x15K\x06e]\x94(K\x14K\x06e]\x94(K\x13K\x06e]\x94(K\x12K\x06e]\x94(K\x11K\x06e]\x94(K\x10K\x06e]\x94(K\x10K\x06e]\x94(K\x0fK\x06e]\x94(K\x0fK\x06ee\x8c\x05tiles\x94]\x94(\x8c\x01H\x94\x8c\x01B\x94e\x8c\x0elast_move_time\x94GA\xd8.=I\x1bK6\x8c\tmove_time\x94G?\xc9\x99\x99\x99\x99\x99\x9a\x8c\x13steps_till_addition\x94K\x01\x8c\x0cstep_counter\x94K\r\x8c\x08move_dir\x94]\x94(K\x00K\x00e\x8c\tdebugList\x94]\x94\x8c\n_MOVEMENTS\x94]\x94(]\x94(J\xff\xff\xff\xffK\x00e]\x94(K\x01K\x00e]\x94(K\x00J\xff\xff\xff\xffe]\x94(K\x00K\x01ee\x8c\x08_dir_ops\x94]\x94(K\x02K\x01K\x04K\x03e\x8c\x05state\x94h\x1c\x8c\rtime_of_death\x94GA\xd8.=Fz7\n\x8c\x0ftime_to_respawn\x94G?\xf8\x00\x00\x00\x00\x00\x00\x8c\x0cgrow_counter\x94K\x00ubJ\x99\xe1\x07\x00h\t)\x81\x94}\x94(h\x0cG@T`\x00\x00\x00\x00\x00h\rG@[ \x00\x00\x00\x00\x00h\x0e\x8c\x012\x94h\x10K\x00h\x11K\x01h\x12K\x00h\x13K\x01h\x14K\x08h\x15K\x08h\x16K\x01h\x17K\x02h\x18M\xcb\x05h\x19K\x01h\x1a\x88h\x1bh\x1ch\x1dK\x00h\x1eK\x02h\x1fG@T`\x00\x00\x00\x00\x00h G@[\x00\x00\x00\x00\x00\x00h!\x88h"G?\xebQ\xa0\xe7\xe2\x06jG\xbf\xe0\xa9\xea\x08LW\xcb\x86\x94ubu\x8c\tlevelname\x94\x8c\x04LEV3\x94\x8c\x06points\x94K\x00ub.'
    testPacketCompressor(data0, data1)
    print('time 4 ms <- expected result');

    # example: case 1
    data0=b'aaaaaaaaaabbbbbbbbbb'
    data1=b'aaaaaaaaaacbbbbbbbbbb'
    testPacketCompressor(data0, data1)
    print('time 4 ms, len=4 data=b\'\\x08\\x00c\\x08\' <- expected result');

    # example: case 2
    data0=b'aaaaaaaaaabbbbbbbbbb'
    data1=b'aaaaaaaaaacaaaaaaaaaa'
    testPacketCompressor(data0, data1)
    print('time 4 ms, len=5 data=b\'\\x08\\x00c\\xf8\\x89\' <- expected result')


class PacketAssembler:
    def __init__(self):
        self.recvData = b''

    def push(self, data):
        self.recvData += data

    def pull(self):
        recvPacket = None
        if len(self.recvData) >= 4:
            length = struct.unpack_from('!I', self.recvData)[0]
            if len(self.recvData) >= 4 + length:
                recvPacket = self.recvData[4:4 + length]
                self.recvData = self.recvData[4 + length:]
                #print('recv:', len(recvPacket), repr(recvPacket))
                return pickle.loads(recvPacket)

    @staticmethod
    def createPacket(content):
        data = pickle.dumps(content)
        #print('send:', len(data))
        return struct.pack('!I', len(data)) + data


class Network:
    def __init__(self, s, host = False):
        self.s = s
        self.host = host
        self.clients = {}
        self.shutdown = False

        self.s.setblocking(0)
        self.s.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)

        self.lock = threading.Lock()
        self.sendPacket = None
        self.recvPacket = None
        self.sendActions = []
        self.recvActions = []
        self.disconnects = []

        if self.host:
            self.thread = threading.Thread(target = self.runServer)
        else:
            self.thread = threading.Thread(target = self.runClient)
        self.thread.start()

    def runServer(self):
        while True:
            inputs = [self.s] + list(self.clients)
            readable, writable, exceptional = select.select(inputs, [], inputs)
            if self.shutdown:
                return

            if self.s in readable:
                c, addr = self.s.accept()
                c.setblocking(0)
                c.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
                with self.lock:
                    self.clients[c] = PacketAssembler()
                print('new client')
                readable.remove(self.s)

            for c in readable:
                try:
                    data = c.recv(4096)
                except ConnectionResetError:
                    with self.lock:
                        self.disconnectClient(c)
                    continue

                with self.lock:
                    if not data:
                        self.disconnectClient(c)
                    else:
                        self.clients[c].push(data)

    def disconnectClient(self, c):
        print('disconnect client')
        del self.clients[c]
        self.disconnects.append(('client-disconnect', c))

    def runClient(self):
        a = PacketAssembler()
        while True:
            inputs = [self.s]
            readable, writable, exceptional = select.select(inputs, [], inputs, 1/30)
            if self.shutdown:
                return

            if readable:
                data = self.s.recv(4096)
                if not data:
                    print('disconnected from server')
                    return

                a.push(data)

            while True:
                packet = a.pull()
                if packet is None:
                    break

                with self.lock:
                    self.recvPacket = packet

            with self.lock:
                if self.sendActions:
                    data = PacketAssembler.createPacket(self.sendActions)
                    try:
                        self.s.sendall(data)
                        self.sendActions = []
                    except BrokenPipeError:
                        return
                    except BlockingIOError:
                        pass

    def stop(self):
        self.shutdown = True
        self.s.shutdown(socket.SHUT_RD)
        self.thread.join()

    def update(self, gameState, actions):
        if self.host:
            with self.lock:
                self.sendPacket = PacketAssembler.createPacket(gameState)
                for c in list(self.clients):
                    try:
                        c.sendall(self.sendPacket)
                    except BrokenPipeError:
                        self.disconnectClient(c)
                    except BlockingIOError:
                        pass

                actions += self.disconnects
                self.disconnects = []

                for c, a in self.clients.items():
                    while True:
                        packet = a.pull()
                        if packet is None:
                            break

                        actions += [('client-actions', c)] + packet

            return gameState, actions
        else:
            with self.lock:
                self.sendActions += actions
                if self.recvPacket is not None:
                    return self.recvPacket, []
            return gameState, []

    def isHost(self):
        return self.host

    def getNumPlayers(self):
        return self.numPlayers