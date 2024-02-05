import numpy as np
import zmq
import time

class GameStimulationEncoder:
    """
    Encodes game metadata and actions into stimulation patterns for optogenetic human cortical organoids,
    operating at a 10Hz rate.
    """
    def __init__(self):
        self.context = zmq.Context()
        # Setup for subscribing to game metadata
        self.subscriber = self.context.socket(zmq.SUB)
        self.subscriber.connect("tcp://*:5556")
        self.subscriber.setsockopt_string(zmq.SUBSCRIBE, '')
        
        # Setup for publishing stimulation patterns
        self.publisher = self.context.socket(zmq.PUB)
        self.publisher.bind("tcp://*:5557")

    def listen_and_process(self):
        # Set up timing for 10Hz operation
        rate = 10  # Hz
        period = 1.0 / rate  # seconds
        next_time = time.time() + period

        while True:
            try:
                while time.time() < next_time:
                    try:
                        metadata_string = self.subscriber.recv_string(zmq.NOBLOCK)
                        metadata = self.parse_metadata_string(metadata_string)
                        if metadata:
                            pattern = self.create_stimulation_pattern(metadata)
                            self.publish_stimulation_pattern(pattern)
                        time.sleep(0.01)  # Short sleep to prevent busy loop
                    except zmq.Again:
                        # No data received, short sleep to prevent busy loop
                        time.sleep(0.01)
                        continue

                # Adjust next_time for the next iteration
                next_time += period
            except Exception as e:
                print(f"An error occurred: {e}")
                # Adjust next_time in case of error to maintain the rate
                next_time += period

    def parse_metadata_string(self, metadata_string):
        metadata = {}
        for item in metadata_string.split(','):
            key, value = item.split(':')
            metadata[key] = float(value)
        return metadata
        
    def create_stimulation_pattern(self, metadata):
        """
        Generates a structured stimulation pattern based on the game's current state.
        """
        pattern_size = 256
        stimulation_pattern = np.zeros((pattern_size, pattern_size), dtype=np.uint8)

        # Example pattern generation logic
        # Varies based on distance to target and player force
        distance_to_target = int(metadata['distance_to_target']) % pattern_size
        player_force = int(metadata['player_force']) % pattern_size
        stimulation_pattern[:, :distance_to_target] = np.linspace(0, 255, distance_to_target).astype(np.uint8).reshape(-1, 1)
        stimulation_pattern[:player_force, :] += np.linspace(0, 255, player_force).astype(np.uint8)

        np.clip(stimulation_pattern, 0, 255, out=stimulation_pattern)  # Ensure values are within byte range
        return stimulation_pattern

    def publish_stimulation_pattern(self, pattern):
        """
        Publishes the stimulation pattern as a serialized string.
        """
        encoded_pattern = np.array2string(pattern.flatten(), separator=',')[1:-1]  # Flatten and trim array brackets
        self.publisher.send_string(encoded_pattern)

if __name__ == "__main__":
    encoder = GameStimulationEncoder()
    encoder.listen_and_process()
