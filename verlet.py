


# velocity verlet


# x = position vector
# v = velocity vector
# a = acceleration vector
# dt = delta time

def integrate1(x, v, a, dt):
    x[0] = x[0] + v[0] * dt + 0.5 * a[0] * dt**2
    x[1] = x[1] + v[1] * dt + 0.5 * a[1] * dt**2
    
    # same as integrate2
    v[0] = v[0] + 0.5 * a[0] * dt
    v[1] = v[1] + 0.5 * a[1] * dt

def integrate2(x, v, a, dt):
    v[0] = v[0] + 0.5 * a[0] * dt
    v[1] = v[1] + 0.5 * a[1] * dt
    
    
# how to use:    
# set/change velocity
# call integrate1
# set/change acceleration
# call integrate2


