import zmq
import time

class ShuffleboardGame:
    def __init__(self, target_distance):
        self.target_distance = target_distance
        self.player_force = 10  # Initial force
        self.score = 0
        self.round = 1
        self.history = []
        self.start_time = time.time()

        # ZeroMQ setup for receiving actions
        self.context = zmq.Context()
        self.sub_socket = self.context.socket(zmq.SUB)
        self.sub_socket.connect("tcp://localhost:5446")
        self.sub_socket.setsockopt_string(zmq.SUBSCRIBE, '')

    def receive_action(self):
        try:
            action_message = self.sub_socket.recv_string(zmq.NOBLOCK)  # Non-blocking
            return action_message
        except zmq.Again:
            # No action received yet
            return None

    def apply_action(self, action):
        if action == 'adjust_force':
            self.player_force += 5  # Example of adjusting force
        elif action == 'fine_tune_force':
            self.player_force += 2  # Fine-tuning force
        elif action == 'execute_shot':
            return self.execute_shot()
        elif action == 'retry_shot':
            self.player_force -= 5  # Decrease force for a retry
        else:
            # Default or unknown action, maintain current force
            pass
        return None

    def execute_shot(self):
        # Simulate shot based on current force
        actual_distance = self.player_force  # Simplified physics
        self.update_state(actual_distance)
        return actual_distance

    def update_state(self, actual_distance):
        current_time = time.time()
        result = {"distance": actual_distance, "force": self.player_force}
        self.history.append({
            'round': self.round,
            'action': 'execute_shot',
            'result': result,
            'timestamp': current_time,
            'distance_to_target': abs(self.target_distance - actual_distance),
            'player_force': self.player_force
        })
        self.score += self.calculate_score(actual_distance)
        self.round += 1

    def calculate_score(self, actual_distance):
        # Scoring logic based on distance to target
        distance_to_target = abs(self.target_distance - actual_distance)
        if distance_to_target == 0:
            return 10
        elif distance_to_target <= 5:
            return 5
        elif distance_to_target <= 10:
            return 3
        else:
            return 1

    def generate_metadata(self):
        duration = time.time() - self.start_time
        return {
            'score': self.score,
            'round': self.round,
            'game_duration': duration,
            'history': self.history
        }

    def play_round(self):
        action = self.receive_action()
        if action:
            result = self.apply_action(action)
            if result is not None:
                print(f"Shot executed with distance {result} and force {self.player_force}")
            metadata = self.generate_metadata()
            print(f"Metadata: {metadata}")

# Inside the ShuffleboardGame class
def publish_metadata(self):
    # Setup a publisher socket if not already done
    publisher = self.context.socket(zmq.PUB)
    publisher.connect("tcp://localhost:5556")  # Connect to the game_to_optical.py subscriber
    
    # Serialize and publish the metadata using a custom string format
    # Example format: "score:10,round:2,duration:120,distance_to_target:5,player_force:15"
    if self.history:
        last_action = self.history[-1]
        distance_to_target = last_action['distance_to_target']
        player_force = last_action['player_force']
    else:
        distance_to_target = self.target_distance  # Default to initial target distance
        player_force = 0  # Default to no force if no history available

    metadata_string = f"score:{self.score},round:{self.round},duration:{time.time() - self.start_time},distance_to_target:{distance_to_target},player_force:{player_force}"
    publisher.send_string(metadata_string)

