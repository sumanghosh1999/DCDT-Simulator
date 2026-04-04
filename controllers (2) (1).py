"""
controllers.py
================

This module defines modular control strategies for the data‑centre
simulator.  A controller reads telemetry from the simulator and
decides how aggressively to operate the cooling units.  Two
controllers are implemented:

PidController – a classical proportional–integral–derivative loop.
  The controller monitors the maximum rack temperature and drives it
  towards a desired setpoint by adjusting the CRAC unit control
  signals.  PID loops are widely used in industrial control systems
  because of their simplicity and robustness.

RLController – a reinforcement learning (RL) agent that
  interacts with the simulator environment in order to minimise a
  cost function (e.g., Power Usage Effectiveness).  Students can
  experiment with their own RL algorithms.  A simple Q‑learning
  implementation is provided here for demonstration; if
  `stable_baselines3` is available, it can optionally be used instead.

In addition, the **ControlSwitch** class provides a unified interface
that can toggle between the PID and RL controllers during runtime.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
try:
    # Attempt to import stable-baselines3.  If unavailable, the code will
    # fallback to a simple Q-learning implementation.  This optional
    # dependency can be installed by students in a Colab environment.
    import gymnasium as gym  # type: ignore
    from stable_baselines3 import PPO  # type: ignore
    from stable_baselines3.common.env_checker import check_env  # type: ignore
    HAS_STABLE_BASELINES = True
except Exception:
    HAS_STABLE_BASELINES = False

from simulator import DataHall


class Controller:
    """Abstract base class for all controllers."""
    def compute_actions(self, hall: DataHall, telemetry: Dict) -> Dict[int, float]:
        """Compute control signals for each cooling unit.

        Parameters
        ----------
        hall : DataHall
            Current simulation instance.
        telemetry : Dict
            Most recent telemetry packet from the simulator.

        Returns
        -------
        actions : dict
            Mapping from cooling unit index to a control signal (0–1).
        """
        raise NotImplementedError


@dataclass
class PidController(Controller):
    """A simple PID controller for data centre cooling.

    The controller attempts to maintain the maximum rack temperature at
    a user‑specified setpoint.  It computes the error (setpoint minus
    measured temperature), integrates it over time and estimates the
    derivative.  The sum of these terms is scaled by gains Kp, Ki and
    Kd to produce a control signal.  The output is clipped to the
    range [0,1] and applied uniformly to all cooling units in the hall.

    This controller is meant as a baseline for comparison with the
    reinforcement‑learning controller.
    """
    setpoint: float = 30.0
    Kp: float = 0.1
    Ki: float = 0.01
    Kd: float = 0.05
    integral: float = 0.0
    previous_error: Optional[float] = None

    def compute_actions(self, hall: DataHall, telemetry: Dict) -> Dict[int, float]:
        # Determine the current maximum temperature in the room
        current = telemetry["room"]["max_temp"]
        error = self.setpoint - current
        # Integrate error
        self.integral += error
        # Derivative term
        derivative = 0.0
        if self.previous_error is not None:
            derivative = error - self.previous_error
        self.previous_error = error
        # PID output
        output = self.Kp * error + self.Ki * self.integral + self.Kd * derivative
        # Convert to a control signal: clamp between 0 and 1
        control = max(0.0, min(1.0, output))
        # Apply the same control to all cooling units
        actions = {idx: control for idx in range(len(hall.cooling_units))}
        return actions


class QLearningAgent:
    """A very simple tabular Q‑learning agent for demonstration.

    This agent discretises the observation (max temperature) into bins
    and learns a Q‑table mapping states to actions.  Students can
    modify the discretisation or reward function for experimentation.
    """
    def __init__(self, n_bins: int = 10, n_actions: int = 3,
                 learning_rate: float = 0.1, discount: float = 0.95, epsilon: float = 0.1):
        self.n_bins = n_bins
        self.n_actions = n_actions
        self.lr = learning_rate
        self.gamma = discount
        self.epsilon = epsilon
        # Initialise Q-table with zeros
        self.q_table = np.zeros((n_bins, n_actions))  # type: ignore

    def discretise(self, value: float, low: float, high: float) -> int:
        # Map a continuous value to a bin index
        value_clamped = max(low, min(high, value))
        ratio = (value_clamped - low) / (high - low)
        return int(ratio * (self.n_bins - 1))

    def choose_action(self, state_bin: int) -> int:
        # e‑greedy policy
        if random.random() < self.epsilon:
            return random.randint(0, self.n_actions - 1)
        return int(np.argmax(self.q_table[state_bin]))  # type: ignore

    def update(self, state_bin: int, action: int, reward: float, next_state_bin: int) -> None:
        # Q-learning update rule
        best_next = np.max(self.q_table[next_state_bin])  # type: ignore
        td_target = reward + self.gamma * best_next
        td_error = td_target - self.q_table[state_bin, action]  # type: ignore
        self.q_table[state_bin, action] += self.lr * td_error  # type: ignore


class RLController(Controller):
    """A reinforcement learning controller for the data centre.

    The RL controller interacts with the simulator as an environment.  At
    each timestep it observes the maximum temperature and issues one
    of three actions: decrease cooling, maintain current cooling or
    increase cooling.  A simple tabular Q‑learning implementation is
    provided.  When `stable_baselines3` is available the user can call
    :meth:`train_stable_baselines` to train a policy using a modern
    RL algorithm such as PPO.

    Notes
    -----
    The controller expects the hall’s cooling unit list to contain at
    least one unit.  It applies the same action to all units for
    simplicity.  Students can extend this class to support
    heterogeneous actions per unit.
    """

    def __init__(self, temp_range: Tuple[float, float] = (15.0, 60.0)):
        self.agent = QLearningAgent()
        self.temp_low, self.temp_high = temp_range
        self.last_state_bin: Optional[int] = None
        self.last_action: Optional[int] = None

    def compute_actions(self, hall: DataHall, telemetry: Dict) -> Dict[int, float]:
        # Observe state (max temperature)
        max_temp = telemetry["room"]["max_temp"]
        state_bin = self.agent.discretise(max_temp, self.temp_low, self.temp_high)
        # Choose an action
        action = self.agent.choose_action(state_bin)
        # Map discrete action to control signal adjustment
        # 0: decrease cooling, 1: no change, 2: increase cooling
        control_adjustments = {0: -0.1, 1: 0.0, 2: 0.1}
        # If there was a previous state, update Q-table with a simple reward
        if self.last_state_bin is not None and self.last_action is not None:
            # Reward is negative of max temperature (lower is better) minus a small cost for cooling power
            reward = -max_temp
            self.agent.update(self.last_state_bin, self.last_action, reward, state_bin)
        # Save current state/action for next update
        self.last_state_bin = state_bin
        self.last_action = action
        # Compute control signals for all cooling units
        actions: Dict[int, float] = {}
        for idx, unit in enumerate(hall.cooling_units):
            # Adjust current control_signal; clamp to [0,1]
            new_signal = unit.control_signal + control_adjustments[action]
            new_signal = max(0.0, min(1.0, new_signal))
            actions[idx] = new_signal
        return actions

    # Optional: training via stable‑baselines3
    def train_stable_baselines(self, hall: DataHall, timesteps: int = 10000) -> None:
        """Train an RL policy using Stable‑Baselines3 PPO, if available.

        Parameters
        ----------
        hall : DataHall
            The simulation environment used for training.  Because
            stable‑baselines3 follows the Gymnasium API, this function
            wraps the hall in a minimal Gym environment.
        timesteps : int, optional
            Number of training timesteps.  A larger value yields a
            better‑trained agent but takes longer to run.
        """
        if not HAS_STABLE_BASELINES:
            raise RuntimeError("stable_baselines3 or gymnasium is not installed. Please install them in Colab.")
        # Define a custom environment that wraps DataHall
        class DataCenterEnv(gym.Env):
            def __init__(self, hall: DataHall):
                super().__init__()
                self.hall = hall
                # Observation: max temperature as a 1‑D array
                self.observation_space = gym.spaces.Box(low=self.temp_low, high=self.temp_high, shape=(1,), dtype=float)
                # Actions: control adjustment {0,1,2}
                self.action_space = gym.spaces.Discrete(3)
            def reset(self, seed: Optional[int] = None, options: Optional[dict] = None):  # type: ignore
                super().reset(seed=seed)
                self.hall.reset()
                telem = self.hall.step()
                max_temp = telem["room"]["max_temp"]
                return np.array([max_temp], dtype=float), {}
            def step(self, action):  # type: ignore
                # Map discrete action to control signal
                control_adjustments = {0: -0.1, 1: 0.0, 2: 0.1}
                for unit in self.hall.cooling_units:
                    unit.control_signal = max(0.0, min(1.0, unit.control_signal + control_adjustments[action]))
                telem = self.hall.step()
                max_temp = telem["room"]["max_temp"]
                reward = -max_temp
                terminated = False
                truncated = False
                return np.array([max_temp], dtype=float), reward, terminated, truncated, {}
        env = DataCenterEnv(hall)
        # Check environment validity
        check_env(env)
        model = PPO("MlpPolicy", env, verbose=0, device="cuda" if torch.cuda.is_available() else "cpu")  # type: ignore
        model.learn(total_timesteps=timesteps)
        # Replace Q-learning agent with the trained policy using a wrapper
        self.sb3_model = model
        def sb3_action(state_bin: int) -> int:
            obs = np.array([float(hall.grid.max())], dtype=float)
            action, _ = self.sb3_model.predict(obs)
            return int(action)
        # monkey‑patch choose_action to use the PPO policy
        self.agent.choose_action = sb3_action  # type: ignore


@dataclass
class ControlSwitch(Controller):
    """Wrap two controllers and allow toggling between them.

    Parameters
    ----------
    pid_controller : PidController
        Controller implementing baseline control logic.
    rl_controller : RLController
        Controller implementing reinforcement learning logic.
    use_rl : bool, optional
        If True the RL controller will be used; otherwise the PID.
    """
    pid_controller: PidController
    rl_controller: RLController
    use_rl: bool = False

    def compute_actions(self, hall: DataHall, telemetry: Dict) -> Dict[int, float]:
        if self.use_rl:
            return self.rl_controller.compute_actions(hall, telemetry)
        else:
            return self.pid_controller.compute_actions(hall, telemetry)

    def toggle(self) -> None:
        """Switch between RL and PID controllers."""
        self.use_rl = not self.use_rl