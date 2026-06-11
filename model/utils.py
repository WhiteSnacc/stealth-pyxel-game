import math

def round_float_if_close(number, delta):
    lower = math.floor(number)
    upper = math.ceil(number)

    # Calculate the difference to the lower and upper integers
    diff_to_lower = abs(number - lower)
    diff_to_upper = abs(number - upper)

    # Determine the closest integer and its difference
    if diff_to_lower <= delta:
        result = lower
    elif diff_to_upper <= delta:
        result = upper
    else:
        result = number

    return int(result)