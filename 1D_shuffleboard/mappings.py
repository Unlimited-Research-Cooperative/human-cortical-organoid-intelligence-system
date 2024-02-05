import zmq
import numpy as np
import time
from collections import defaultdict
from datetime import datetime, timedelta
from matplotlib import pyplot as plt
from matplotlib.animation import FuncAnimation

class ActionFeedbackReceiver:
    """
    Receives feedback on actions taken in the game, indicating success or need for adjustment.
    """
    def __init__(self, zmq_context, feedback_sub_address="tcp://localhost:5557"):
        self.sub_socket = zmq_context.socket(zmq.SUB)
        self.sub_socket.connect(feedback_sub_address)
        self.sub_socket.setsockopt_string(zmq.SUBSCRIBE, '')

    def receive_feedback(self):
        feedback = defaultdict(list)
        try:
            while True:
                message = self.sub_socket.recv_string(zmq.NOBLOCK)
                action, success = message.split(':')
                feedback[action].append(bool(int(success)))
        except zmq.Again:
            pass
        return feedback

class ActionSuccessLogger:
    """
    Logs success metrics for actions to assess and adjust mapping quality over time.
    """
    def __init__(self):
        self.action_log = defaultdict(list)

    def log_feedback(self, feedback):
        for action, outcomes in feedback.items():
            self.action_log[action].extend(outcomes)

    def get_action_success_rate(self, action):
        if action not in self.action_log or not self.action_log[action]:
            return 0
        successes = self.action_log[action]
        return sum(successes) / len(successes)

class MappingQualityVisualizer:
    """
    Visualizes the quality of action mappings based on success rates.
    """
    def __init__(self, action_logger):
        self.action_logger = action_logger
        self.fig, self.ax = plt.subplots()

    def update_plot(self, frame):
        actions = list(self.action_logger.action_log.keys())
        success_rates = [self.action_logger.get_action_success_rate(action) for action in actions]
        self.ax.clear()
        self.ax.bar(actions, success_rates)
        self.ax.set_ylim(0, 1)
        self.ax.set_title('Action Mapping Quality Scores')
        self.ax.set_xlabel('Action')
        self.ax.set_ylabel('Success Rate')

    def animate(self):
        animation = FuncAnimation(self.fig, self.update_plot, interval=1000)
        plt.show()

if __name__ == "__main__":
    zmq_context = zmq.Context()
    feedback_receiver = ActionFeedbackReceiver(zmq_context)
    action_logger = ActionSuccessLogger()
    visualizer = MappingQualityVisualizer(action_logger)

    # Periodically receive feedback and update action success rates
    last_update = datetime.now()
    while True:
        feedback = feedback_receiver.receive_feedback()
        action_logger.log_feedback(feedback)

        current_time = datetime.now()
        if current_time - last_update > timedelta(seconds=10):  # Update visualizer every 10 seconds
            visualizer.animate()
            last_update = current_time
