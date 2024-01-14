import random

def shuffleboard_game(action, target_distance):
    """
    Simulate a round of the 1D shuffleboard game.

    Parameters:
    action (int): The power of the shot, determined by the control system.
    target_distance (int): The target distance the player aims to achieve.

    Returns:
    int: The actual distance the puck traveled.
    """

    # Simulate the actual distance based on the action and some randomness
    actual_distance = action + random.randint(-10, 10)  # Adding randomness to the shot

    return actual_distance
