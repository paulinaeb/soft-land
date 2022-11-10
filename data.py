# constants
# colors in hsv dict for masks. the first value represents the lower limit and the second the lower
HSV_COLORS = {
    'blue': [[90,60,0], [121,255,255]], 
    'green': [[50, 100,100], [70,255,255]],
    'yellow': [[20, 100, 100], [30, 255, 255]],
    'black': [[0, 0, 0], [180,255,30]],
    'orange':[[10, 100, 20], [25, 255, 255]],
    'red': [[0, 100, 20], [10, 255, 255]],
    'red2':[[160, 100, 20], [179, 255, 255]]
}

# viewport new values
NEW_MIN_X = 0
NEW_MIN_Y = 0
# real values in cm of projection
NEW_MAX_Y = 62
NEW_MAX_X = 104