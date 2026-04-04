# DCDT-Simulator

Project User Guide

Project: Data Center Digital Twin (DCDT) Simulator
Thread: Distributed Systems and Software (DSSD)

This user guide provides comprehensive step-by-step instructions to set up, run, and extend the Data Centre Digital Twin (DCDT) simulator. It draws on the provided Jupyter notebooks and Python scripts to help you re‑create and experiment with the project on your own. The guide is written for students interested in the Distributed Systems and Software Design (DSSD) thread, but is also accessible to anyone interested in data‑center simulation and control, also digital twin systems.

Contents
1.	Getting Started
2.	Controller Modifications
3.	Simulator Modification
4.	Data Source Replacement
5.	File Descriptions
6.	Links & References


1. Getting Started
This section walks you through the essential steps to set up and run the DCDT simulator using the provided Jupyter notebooks. The instructions assume you are working in a Jupyter environment such as Google Colab.
Step 1: Open the Tutorial Notebook
Start by opening the tutorial notebook on Google Colab or your local Jupyter server. The first notebook (‘DCDT_Tutorial_Part1.ipynb’) introduces you to the basics of the simulator. In Colab, you can drag and drop the notebook into the file pane and click to open it. The first markdown cell describes the project and its objectives, while the second cell presents the modelling principles behind the simulator. Make sure
Step 2: Install Optional Dependencies
If you wish to train a reinforcement‑learning (RL) agent using modern algorithms like PPO, you need to install additional packages. In the notebook, run the following cell (it may take a few minutes):
!pip install -q stable-baselines3 shimmy gymnasium plotly
This command installs the ‘gymnasium’, ‘stable‑baselines3’, ‘shimmy’, and ‘plotly’ libraries. They enable RL training and rich visualisations. If you are only using the built-in PID controller, you can skip this step.
Step 3: Construct the Data Hall
The next cell constructs the data hall using the interactive grid editor. This tool lets you place server racks and cooling units on a grid. The grid editor is provided by the ‘grid_editor’ module. Run the following code cell:
from grid_editor import create_grid

server_racks = []
cooling_systems = []

# Initialise Data Hall Grid
rows = 10  # adjust as required
cols = 10  # adjust as required

server_racks, cooling_systems = create_grid(rows, cols)

When the cell runs, a grid appears.
 
Single‑click a cell to place a server rack (green) and double‑click to place a cooling unit (blue).
 
After making your selections, click Submit (button works only when at least one cell is selected) to save the coordinates. The selected positions are stored in the global lists ‘server_racks’ and ‘cooling_systems’, which will be used to build the simulator.
 
Step 4: Create the Simulation, Controller and Dashboard
Once you have designed the hall layout, create the simulator, the control objects, and the dashboard to visualise results. Use the following code:
from simulator import create_default_hall
from controllers import PidController, RLController, ControlSwitch
from dashboard import Dashboard

# Build the data hall
hall = create_default_hall(server_racks, cooling_systems, rows, cols)

# Create controllers
pid_controller = PidController(setpoint=30.0)
rl_controller  = RLController()

# Wrap both controllers with a switch
controller = ControlSwitch(pid_controller=pid_controller, rl_controller=rl_controller, use_rl=False)

# Create a dashboard
dash = Dashboard(hall=hall, controller=controller)
This cell imports the simulation and controller classes from the corresponding modules. The ‘create_default_hall’ function builds the hall object with the selected rack and cooling locations. Two controllers are instantiated: a PID controller with a 30 °C setpoint, and an RL controller. They are wrapped in a ‘ControlSwitch’ object, which allows toggling between them during the simulation. Finally, a ‘Dashboard’ object is created to visualise the thermal map, PUE curve and power usage.
Step 5: Run the Simulation
Now you can run the thermal simulation and watch the system evolve over time. The following loop advances the physics, computes the control signals, updates the cooling units, and refreshes the dashboard:
from IPython.display import clear_output, display
import time
import random

# Simulation parameters, using small dt for thermal stability
steps  = 200   # number of simulation steps
dt_val = 0.05  # time interval (seconds)

for i in range(steps):
    # Step the physics
    telemetry = hall.step(dt=dt_val)

    # Switch to RL control halfway
    if i == int(steps/2):
        controller.toggle()

    # Compute and apply actions
    actions = controller.compute_actions(hall, telemetry)
    for idx, signal in actions.items():
        hall.cooling_units[idx].control_signal = signal

    # Refresh the UI every 2 steps
    if i % 2 == 0:
        clear_output(wait=True)
        fig = dash.update(telemetry)
        fig.show()
        mode_label = "RL (Q‑Learning)" if controller.use_rl else "PID (Baseline)"
        print(f"Step {i+1}/{steps} | Mode: {mode_label}")
        print(f"Time {telemetry['time']:.1f}s, PUE={telemetry['pue']:.3f}, MaxTemp={telemetry['room']['max_temp']:.2f}°C")
    time.sleep(1.0)  # frame rate control
This loop performs the following actions:
•	Steps the physics using ‘hall.step(dt)’, which updates the temperature grid according to a finite difference scheme.
•	At halfway through the run, toggles the controller to RL mode by calling ‘controller.toggle()’.
•	Computes control actions using the currently selected controller and applies them to each cooling unit.
•	Updates the dashboard every few steps. The heatmap displays the thermal gradient, the top-right plot shows the PUE curve, and the bottom-right plot shows total power usage.
Because the dashboard refreshes live, the simulation delays for one second per frame to make the animation smooth.
 
Step 6: Log Simulation Data
After running the simulation, you may wish to log the telemetry for further analysis. The ‘logger’ module provides a ‘TelemetryLogger’ class for this purpose. The following cell stores the final timestep and exports it as a CSV file:
from logger import TelemetryLogger
import pandas as pd

# Export final state
logger = TelemetryLogger()
logger.append(telemetry)
logger.export_csv("final_telemetry_log.csv")

print("Telemetry successfully exported to final_telemetry_log.csv.")
display(pd.read_csv("final_telemetry_log.csv").head())
To log every timestep instead of just the final state, create a ‘TelemetryLogger’ instance before the loop, call ‘logger.append(telemetry)’ inside the loop, and then call ‘export_csv()’ after the loop completes. The logger flattens nested structures when exporting to CSV, making it easy to analyse results in a spreadsheet or plotting tool.
Step 7: Run Fault Testing Simulation
The second notebook (‘DCDT_Tutorial_Part2.ipynb’) extends the same setup to perform fault testing. You reuse the same grid editor to create the hall and then inject faults to see how the system responds. Begin by constructing the hall and controllers again:
from simulator import create_default_hall
from controllers import PidController, RLController, ControlSwitch
from dashboard import Dashboard

# Build the data hall for fault testing
hall_faulty = create_default_hall(server_racks, cooling_systems, rows, cols)

# Create controllers
pid_controller2 = PidController(setpoint=30.0)
rl_controller2 = RLController()

# Wrap both controllers with a switch
controller2 = ControlSwitch(pid_controller=pid_controller2, rl_controller=rl_controller2, use_rl=False)

# Create a dashboard for fault testing
dash2 = Dashboard(hall=hall_faulty, controller=controller2)
 
Next, define simulation parameters and fault injection rates. Fan faults simulate a failed rack fan (reducing cooling efficiency), and spike faults simulate sudden workload spikes. The following code runs the simulation with fault injection:
from IPython.display import clear_output, display
import time
import random

# Simulation parameters
steps   = 200
dt_val  = 0.1
fan_fault_frac   = 0.20  # 20% of racks
spike_fault_frac = 0.50  # 50% of racks
N_fault_fan   = int(fan_fault_frac * len(server_racks))
N_fault_spike = int(spike_fault_frac * len(server_racks))

for i in range(steps):
    # Step the physics
    telemetry2 = hall_faulty.step(dt=dt_val)

    # Switch to RL control halfway
    if i == int(steps/2):
        controller2.toggle()

    # Fan fault injection at quarter and two‑thirds of the run
    if i == int(steps/4) or i == int(2*steps/3):
        for _ in range(N_fault_fan):
            hall_faulty.inject_fault(random.randint(0, len(server_racks) - 1), "fan")

    # Spike fault injection at one‑third and three‑quarters of the run
    if i == int(steps/3) or i == int(3*steps/4):
        for _ in range(N_fault_spike):
            hall_faulty.inject_fault(random.randint(0, len(server_racks) - 1), "spike")

    # Compute and apply actions
    actions2 = controller2.compute_actions(hall_faulty, telemetry2)
    for idx, signal in actions2.items():
        hall_faulty.cooling_units[idx].control_signal = signal

    # Refresh the UI every 2 steps
    if i % 2 == 0:
        clear_output(wait=True)
        fig2 = dash2.update(telemetry2)
        fig2.show()
        mode_label = "RL (Q‑Learning)" if controller2.use_rl else "PID (Baseline)"
        print(f"Step {i+1}/{steps} | Mode: {mode_label}")
        print(f"Time {telemetry2['time']:.1f}s, PUE={telemetry2['pue']:.3f}, MaxTemp={telemetry2['room']['max_temp']:.2f}°C")
    time.sleep(1.0)
In this fault‑testing scenario, fan faults increase rack exhaust temperature by multiplying it by 1.5, while spike faults temporarily set the rack’s CPU load to 100 %. Observing the dashboard during these injections helps you understand how faults influence thermal behaviour, power consumption and PUE. You can reset faults during the run using ‘hall_faulty.inject_fault(rack_id, "reset")’ to restore a rack to nominal operation.

After the fault testing simulation, you can log the final timestep using the logger in the same way as before. To capture the full trajectory, initialise the logger before the loop and append telemetry inside the loop.
2. Controller Modifications
The DCDT simulator supports two control strategies out of the box: a classical PID controller and a reinforcement‑learning controller. This section shows how to modify these controllers or integrate your own. All controller classes are defined in ‘controllers.py’.
2.1 Tuning the PID Controller
The PID controller maintains the maximum rack temperature at a desired setpoint. It computes an error term (setpoint minus current max temperature), integrates it over time, and includes a derivative term based on the change in error. These terms are scaled by gains ‘Kp’, ‘Ki’ and ‘Kd’. The output is clipped between 0 and 1 to produce a control signal for each cooling unit. The ‘PidController’ class has the following attributes and method:
@dataclass
class PidController(Controller):
    setpoint: float = 30.0
    Kp: float = 0.1 
    Ki: float = 0.01
    Kd: float = 0.05
    integral: float = 0.0
    previous_error: Optional[float] = None

    def compute_actions(self, hall: DataHall, telemetry: Dict) -> Dict[int, float]:
        current    = telemetry["room"]["max_temp"]
        error      = self.setpoint - current
        self.integral += error
        derivative = 0.0
        if self.previous_error is not None:
            derivative = error - self.previous_error
        self.previous_error = error
        output = self.Kp * error + self.Ki * self.integral + self.Kd * derivative
        control = max(0.0, min(1.0, output))
        actions = {idx: control for idx in range(len(hall.cooling_units))}
        return actions
To tune the PID controller, adjust the ‘setpoint’ and the gains ‘Kp’, ‘Ki’, and ‘Kd’. A higher ‘Kp’ makes the controller respond more aggressively to temperature deviations; increasing ‘Ki’ improves steady‑state accuracy by accumulating error; and ‘Kd’ dampens oscillations by reacting to the rate of change. You can also modify the output scaling or apply different control signals to individual cooling units. The baseline implementation uses the same control output for all units, but you can change ‘compute_actions’ to compute a distinct signal for each unit, depending on its local temperature.
2.2 Modifying the RL Controller
The Reinforcement‑Learning controller uses a simple tabular Q‑learning agent by default. It discretises the maximum room temperature into bins and selects actions to decrease, maintain or increase cooling. The core functions of the RL controller are as follows:
class RLController(Controller):
    def __init__(self, temp_range=(15.0, 60.0)):
        self.agent = QLearningAgent()
        self.temp_low, self.temp_high = temp_range
        self.last_state_bin: Optional[int] = None
        self.last_action: Optional[int] = None

    def compute_actions(self, hall: DataHall, telemetry: Dict) -> Dict[int, float]:
        max_temp = telemetry["room"]["max_temp"]
        state_bin = self.agent.discretise(max_temp, self.temp_low, self.temp_high)
        action = self.agent.choose_action(state_bin)
        control_adjustments = {0: -0.1, 1: 0.0, 2: 0.1}
        if self.last_state_bin is not None and self.last_action is not None:
            reward = -max_temp
            self.agent.update(self.last_state_bin, self.last_action, reward, state_bin)
        self.last_state_bin = state_bin
        self.last_action = action
        actions: Dict[int, float] = {}
        for idx, unit in enumerate(hall.cooling_units):
            new_signal = unit.control_signal + control_adjustments[action]
            new_signal = max(0.0, min(1.0, new_signal))
            actions[idx] = new_signal
        return actions
You can modify several aspects of the RL controller:
•	Number of bins and actions: The ‘QLearningAgent’ discretizes the temperature range into ‘n_bins’ and defines ‘n_actions’. Increasing the number of bins gives a finer discretization at the cost of a larger Q‑table.
•	Reward function: The default reward is the negative of the maximum temperature. You can incorporate power consumption, PUE, or other metrics into the reward to encourage efficient operation.
•	Policy update: The Q‑learning update uses a learning rate (‘lr’), discount factor (‘gamma’), and exploration rate (‘epsilon’). Adjust these parameters to influence learning speed and exploration.
•	Stable‑Baselines training: If ‘stable‑baselines3’ is installed, call ‘rl_controller.train_stable_baselines(hall, timesteps=50000)’ to train a PPO agent in a more robust environment. This requires converting the simulator into a Gymnasium environment and may provide better performance than tabular Q‑learning.
3. Simulator Modification
The ‘DataHall’ class implements the core thermal physics and is defined in ‘simulator.py’. The hall maintains a grid of temperatures and lists of ‘ServerRack’ and ‘CoolingUnit’ objects. Temperatures evolve according to a simple finite difference scheme: at each internal grid point, the new temperature tends towards the average of its four neighbours (up, down, left, right). This discrete approximation is analogous to the continuous heat‑conduction equation where the temperature at a node equals the average of its neighbours. Racks add heat proportional to their power draw, while cooling units remove heat based on a setpoint and control signal. PUE is computed as total facility power divided by IT power.
3.1 Changing Grid Size and Layout
You can change the physical size of the simulated hall by adjusting the ‘rows’ and ‘cols’ parameters when calling ‘create_grid()’. Larger grids provide higher spatial resolution but require more computation. After generating the hall, you can assign server racks and cooling units to different coordinates to explore alternative layouts. Think about placing cooling units near hot spots or distributing racks evenly to prevent thermal bottlenecks.
3.2 Modifying Rack and Cooling Parameters
Each ‘ServerRack’ has attributes for CPU load, base power, maximum power, and a fan failure multiplier. You can set these attributes manually to create heterogeneous racks or simulate varying workloads. For example, to double the idle power of a particular rack, set ‘rack.base_power = 1000.0’ before running the simulation. Similarly, the ‘CoolingUnit’ class exposes a ‘setpoint’ and a ‘max_cooling_power’. Lowering the setpoint increases cooling aggressiveness, and increasing ‘max_cooling_power’ allows the unit to extract more heat.
3.3 Adjusting Thermal Physics
The ‘DataHall.step()’ method updates the temperature grid by blending each cell towards the average of its four neighbours and adding rack and cooling contributions. If you wish to implement more sophisticated physics, you can modify this method. For example, you could introduce anisotropic thermal conductivity, add convective air flows, or incorporate heat accumulation over time. Such modifications require careful numerical stability analysis but offer a richer representation of real data centres. Remember that stability often depends on the timestep ‘dt’ and grid spacing; a smaller ‘dt’ yields more stable results at the cost of slower simulations.
4. Data Source Replacement: Switching to Real‑World Data
In the baseline simulator, CPU loads and faults are synthetic. To make the simulation more realistic, you can feed real sensor data or workload traces into the model. Here is a general approach:
4.1 Collect Real Sensor Data
Gather temperature and power readings from sensors in an actual data centre or from publicly available datasets. Ensure that the measurements correspond to the positions of racks and cooling units in the simulated grid. Each data record should include a timestamp, rack identifier, inlet temperature, exhaust temperature, and power draw.
4.2 Integrate Data into the Simulator
Modify the ‘ServerRack.update()’ method to accept sensor readings as inputs instead of computing heat generation purely from CPU load. For example, you could read a CSV file into a dictionary mapping ‘(time, rack_id)’ to measured power and then update the rack’s ‘power_draw’ accordingly. Likewise, adjust the control logic to work with real inlet temperatures by setting ‘rack.inlet_temp’ to the measured value.
4.3 Feeding Real Loads
If you have trace data for CPU utilisation, assign these values to ‘rack.cpu_load’ over time. This approach enables the simulation to replicate the dynamic workload patterns observed in production systems. Combined with real temperature sensors, the twin becomes a powerful tool for testing control algorithms under realistic conditions.
When working with real data, consider the sampling rate, data quality, and missing values. Preprocess your data to fill gaps and align timestamps with the simulation timestep. You can also connect the logger to a time‑series database or MQTT broker for continuous real‑time operation.
5. File Descriptions
This project includes several Python scripts and notebooks. Understanding their structure helps you extend or modify the simulator. The following subsections describe each file briefly and provide key code excerpts.
5.1 Tutorial Notebooks
DCDT_Tutorial_Part1.ipynb: Demonstrates how to set up the hall, run a simulation using a PID and RL controller, and export telemetry. The notebook explains modelling principles, optional package installation, grid construction, simulator creation, the main simulation loop, and data logging.
DCDT_Tutorial_Part2.ipynb: Extends Part 1 to inject faults into the system. It introduces additional code to calculate the number of racks affected by fan and spike faults, injects them at specified timesteps, and shows how the system responds. The conclusion suggests further experiments such as new layouts, varying fault sequences, training RL policies and modifying the reward function.
5.2 simulator.py
Defines the core simulator. It contains data classes for ‘ServerRack’ and ‘CoolingUnit’ and the ‘DataHall’ class. The ‘DataHall’ maintains a temperature grid, calculates heat flows using a finite difference scheme, updates racks and cooling units, computes PUE, and supports fault injection. The continuous heat‑conduction equation is approximated discretely so that the temperature at an internal node equals the average of its four neighbours. PUE is calculated as the ratio of total facility power to IT power.
5.3 controllers.py
Implements control strategies. The ‘PIDController’ class performs Proportional-Integral-Derivative control and sends the same control signal to all cooling units. The ‘RLController’ wraps a Q‑learning agent and updates its policy online based on the maximum room temperature. The file also contains an optional method to train an RL policy using stable‑baselines if the package is available. Finally, ‘ControlSwitch’ toggles between controllers at runtime.
5.4 grid_editor.py
Provides an interactive GUI for selecting server racks and cooling units. It displays a grid of cells in Colab; a single click places a rack and a double click places a cooling unit. After submission, the chosen coordinates are returned to Python. The file defines a global ‘server_racks’ and ‘cooling_systems’ list and includes CSS/JS code to draw icons and manage user interactions.
5.5 dashboard.py
Visualises the simulation state. It uses Plotly to generate a heatmap of the temperature grid and two line charts for PUE and power usage. The dashboard accumulates time, PUE and power values to show trends over the simulation. It resets its history after a defined number of steps to avoid memory buildup.
5.6 logger.py
Implements a simple telemetry logger. It collects dictionaries emitted by the simulator and exports them to JSON or CSV. The CSV export flattens nested data structures so that each rack’s power draw and the room metrics become separate columns. Students can extend this class to push data to external systems.
6. Links & References
The following links and references were used in the preparation of this guide and provide additional context:
•	https://en.wikipedia.org/wiki/Power_usage_effectiveness
•	https://www.techtarget.com/searchdatacenter/definition/power-usage-effectiveness-PUE
•	https://gymnasium.farama.org/introduction/migration_guide/
•	https://pypi.org/project/stable-baselines3/
•	https://www.energy.gov/articles/doe-releases-new-report-evaluating-increase-electricity-demand-data-centers
•	https://moodle2.units.it/pluginfile.php/598351/mod_resource/content/9/FD_handout19.03.2024.pdf
•	https://www.socomec.us/en-us/solutions/business/data-centers/understanding-power-consumption-data-centers
•	https://www.parkplacetechnologies.com/blog/data-center-cooling-systems-benefits-comparisons/



Statement of AI Usage:
Multiple AI tools including: ChatGPT (exploring, ideation and discretization code for the physics engine), Gemini(for exploration, ideation, helper script codes) and NotebookLM+Microsoft ClipChamp (for video editing); were utilized in this project.


