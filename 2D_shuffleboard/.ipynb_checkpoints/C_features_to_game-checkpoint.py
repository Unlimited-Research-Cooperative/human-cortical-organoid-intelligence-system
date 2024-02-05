import zmq
import time

class FeaturesToGameAction:
    def __init__(self):
        self.context = zmq.Context()
        self.sub_socket = self.context.socket(zmq.SUB)
        self.sub_socket.connect("tcp://localhost:5445")
        self.sub_socket.setsockopt_string(zmq.SUBSCRIBE, '')
        self.retry_interval = 1 / 10  # Retry interval to attempt receiving at 10Hz update rate

        self.feature_to_action_map = {
            'variance': ('adjust_aim', 0.2),  # Adjust aim if variance exceeds a threshold, indicating potential strategy change
            'std_dev': ('increase_force', 0.1),  # Increase force if standard deviation is low, suggesting a more forceful shot might be needed
            'rms': ('decrease_force', 0.5),  # Decrease force if RMS value is high, to avoid overshooting
            'peak_counts': ('execute_shot', 5),  # Execute shot if peak count exceeds threshold, suggesting readiness to shoot
            'band_features': {
                'delta': ('calm_strategy', 0.3),  # Lower delta band power might indicate a calm strategy adjustment
                'theta': ('focus_aim', 0.5),  # Higher theta might indicate focusing aim
                'alpha': ('relax_force', 0.7),  # Alpha band adjustments might indicate relaxing force
                'beta': ('alert_adjust', 1.0),  # Beta increases could indicate need for alert adjustments in strategy
            },
            'spectral_entropy': ('strategic_shift', 0.8),  # High spectral entropy might indicate a strategic shift
            'centroids': ('precision_aim', 0.4),  # Spectral centroids could relate to precision aiming adjustments
            'spectral_edge_densities': ('edge_tactic', 0.9),  # Edge density might suggest an edge tactic adjustment
            'phase_synchronization': ('team_sync', 0.7),  # If applicable, synchronize with team strategy
            'higuchi_fractal_dimension': ('complex_strategy', 1.2),  # Complexity in signal might suggest a complex strategic adjustment
            'zero_crossing_rate': ('steady_aim', 0.1),  # Low activity might suggest steadying aim before a shot
            'empirical_mode_decomposition': ('adaptive_strategy', 0.5),  # Use EMD analysis for adaptive strategy changes
            'time_warping_factor': ('timing_adjust', 0.3),  # Adjust timing of shots based on warping factor
            'evolution_rate': ('force_modulation', 0.6),  # Modulate force based on signal evolution rate
        }


    def decode_signal_features(self):
        while True:
            try:
                message = self.sub_socket.recv_string(flags=zmq.NOBLOCK)
                # Assuming the message is a simple string representing a single feature for simplicity
                feature_value = float(message)
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
        This example uses a single feature value for simplicity; expand logic as needed.
        """
        # Example: Determine action based on feature value thresholds
        if feature_value > 0.5:
            return 'perform_action_1'
        elif feature_value <= 0.5:
            return 'perform_action_2'
        else:
            return 'default_action'

    def process_actions(self, action):
        # Implement game logic or action execution based on decoded action
        print(f"Action to perform: {action}")

def main():
    features_to_action = FeaturesToGameAction()
    
    while True:
        action = features_to_action.decode_signal_features()
        if action:
            features_to_action.process_actions(action)
            # Ensure consistent processing rate
            time.sleep(1 / 10)

if __name__ == "__main__":
    main()
