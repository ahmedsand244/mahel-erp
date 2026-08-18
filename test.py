def trap_rain_water(height):
    """
    Calculate the total amount of rainwater trapped between towers.
 
    Input:
        height (list[int]): Heights of the towers.
 
    Output:
        int: Total trapped rainwater.
    """
 
    if not height:
        return 0
 
    left = 0
    right = len(height) - 1
 
    left_max = 0
    right_max = 0
    water = 0
 
    while left < right:
 
        # Process the side with the smaller current height.
        if height[left] <= height[right]:
 
            if height[left] >= left_max:
                left_max = height[left]
            else:
                water += left_max - height[left]
 
            left += 1
 
        else:
 
            if height[right] >= right_max:
                right_max = height[right]
            else:
                water += right_max - height[right]
 
            right -= 1
 
    return water
 
 
# Test cases
test_cases = [
    [4, 2, 0, 3, 2, 5],
    [7, 0, 4, 2, 5, 0, 6, 4, 0, 5],
    [5, 0, 0, 2, 0, 4]
]
 
for heights in test_cases:
    result = trap_rain_water(heights)
    print("Input :", heights)
    print("Output:", result)
    print()
