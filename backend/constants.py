# Define namespaces for easier access
NS = {
    "bpmn": "http://www.omg.org/spec/BPMN/20100524/MODEL",
    "bpmndi": "http://www.omg.org/spec/BPMN/20100524/DI",
    "omgdc": "http://www.omg.org/spec/DD/20100524/DC",
    "ns6": "http://www.omg.org/spec/DD/20100524/DI",
}

# Define required constants (lane width needs to be adjusted dynamically with respect to the diagram width)
LANE_HEIGHT = 200
INITIAL_LANE_HORIZONTAL_SHIFT_LEFT = 100
INITIAL_LANE_HORIZONTAL_SHIFT_RIGHT = 250
INITIAL_LANE_VERTICAL_SHIFT = 20
