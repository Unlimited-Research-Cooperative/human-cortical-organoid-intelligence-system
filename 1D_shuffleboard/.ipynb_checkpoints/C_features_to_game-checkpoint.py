import zmq
import time

class FeaturesToGameAction:
    def __init__(self):
        self.context = zmq.Context()
        self.sub_socket = self.context.socket(zmq.SUB)
        self.sub_socket.connect("tcp://localhost:5445")
        self.sub_socket.setsockopt_string(zmq.SUBSCRIBE, '')
        self.retry_interval = 1 / 10  # Retry interval to attempt receiving at 10Hz update rate

        # Adjusted feature-to-action mappings for 1D shuffleboard
        self.feature_to_action_map = {
            'variance': ('adjust_force', 0.2),  # Adjust force based on variance, indicating a need for more or less power
            'std_dev': ('fine_tune_force', 0.1),  # Fine-tune force if standard deviation is low
            'rms': ('execute_shot', 0.5),  # Execute shot if RMS value is high, indicating optimal shot power
            'peak_counts': ('retry_shot', 3),  # Retry shot if peak count is high, suggesting a missed opportunity
            # Simplified the action mapping to better fit the 1D shuffleboard context
        }

    def decode_signal_features(self):
        while True:
            try:
                message = self.sub_socket.recv_string(flags=zmq.NOBLOCK)
                feature_value = float(message)  # Assuming a single feature value for simplicity
                return self.translate_features_to_action(feature_value)
            except zmq.Again:
                time.sleep(self.retry_interval)  # Wait before retrying
                continue
            except ValueError:
                print("Error decoding feature value")
                return None

    def translate_features_to_action(self, feature_value):
        """
        Translate the decoded signal feature value into a game action.
        Adjusted for the context of a 1D shuffleboard game.
        """
        if feature_value > 0.5:
            return 'increase_force'
        elif feature_value <= 0.5:
            return 'decrease_force'
        else:
            return 'maintain_force'

    def process_actions(self, action):
        # Implement action execution based on decoded action
        print(f"Action to perform: {action}")

def main():
    features_to_action = FeaturesToGameAction()
    
    while True:
        action = features_to_action.decode_signal_features()
        if action:
            features_to_action.process_actions(action)
            time.sleep(1 / 10)  # Ensure consistent processing rate

if __name__ == "__main__":
    main()
