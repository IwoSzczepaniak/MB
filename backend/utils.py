import pm4py
import xml.etree.ElementTree as ET
import pandas as pd

from typing import Tuple, List, Union, Dict
from constants import *


def get_most_top_left_position(root: ET.Element) -> Tuple[float, float]:
    bpmn_plane = find_BPMN_plane(root)

    x_positions = []
    y_positions = []
    for element in bpmn_plane.iter():
        if element.tag.endswith("Bounds"):
            x_positions.append(element.get("x"))
            y_positions.append(element.get("y"))
    x_positions = [float(x) for x in x_positions if x is not None]
    y_positions = [float(y) for y in y_positions if y is not None]
    return min(x_positions), min(y_positions)


def get_most_top_right_position(root: ET.Element) -> Tuple[float, float]:
    bpmn_plane = find_BPMN_plane(root)

    x_positions = []
    y_positions = []
    for element in bpmn_plane.iter():
        if element.tag.endswith("Bounds"):
            x_positions.append(element.get("x"))
            y_positions.append(element.get("y"))
    x_positions = [float(x) for x in x_positions if x is not None]
    y_positions = [float(y) for y in y_positions if y is not None]
    return max(x_positions), min(y_positions)


def get_lane_count(root: ET.Element) -> int:
    bpmn_plane = find_BPMN_plane(root)

    lane_count = 0
    for element in bpmn_plane.iter():
        if element.tag.endswith("BPMNShape") and element.get("id").startswith("Lane"):
            lane_count += 1

    return lane_count


def add_lane_set(root: ET.Element, lane_set_name: str) -> ET.Element:
    parent_process = find_bpmn_process(root)
    return ET.SubElement(
        parent_process,
        f"{{{NS['bpmn']}}}laneSet",
        {"id": f"LaneSet_{lane_set_name}", "name": lane_set_name},
    )


def add_lane(root: ET.Element, lane_name: str) -> ET.Element:
    parent_lane_set = find_lane_set(root)
    return ET.SubElement(
        parent_lane_set,
        f"{{{NS['bpmn']}}}lane",
        {
            "id": f"Lane_{lane_name}",
            "name": lane_name,
        },
    )


def add_lane_di(root: ET.Element, lane: ET.Element) -> Tuple[float, float, str]:
    # since logic for calculating lane count is based on graphical elements,
    # the count is queried before the creation of new graphical lane
    lane_count = get_lane_count(root)

    bpmn_plane = find_BPMN_plane(root)
    shape = ET.SubElement(
        bpmn_plane,
        f"{{{NS['bpmndi']}}}BPMNShape",
        {"id": f"{lane.get('id')}_di", "bpmnElement": f"{lane.get('id')}"},
    )

    x, y = get_most_top_left_position(root)
    LANE_WIDTH, _ = get_most_top_right_position(root)

    # the width of the lane needs to be adjusted to the size of BPMN Diagram and extended a bit more to the right just to look better
    LANE_WIDTH = LANE_WIDTH + INITIAL_LANE_HORIZONTAL_SHIFT_RIGHT
    if lane_count == 0:
        # first graphical lane needs to be shifted to the left and top - just for visualization purposes
        x = x - INITIAL_LANE_HORIZONTAL_SHIFT_LEFT
        y = y - INITIAL_LANE_VERTICAL_SHIFT
    else:
        # new lanes needs to be placed lower to avoid overlapping with previously created ones
        y = y + lane_count * LANE_HEIGHT

    bounds = ET.SubElement(
        shape,
        f"{{{NS['omgdc']}}}Bounds",
        {
            "x": str(x),
            "y": str(y),
            "width": str(LANE_WIDTH),
            "height": str(LANE_HEIGHT),
        },
    )

    return x, y, lane.get("id")


# unique fields are process or laneSet or BPMNPlane and possibly few more
def find_unique_field(root: ET.Element, suffix: str) -> Union[ET.Element, None]:
    for element in root.iter():
        if element.tag.endswith(suffix):
            return element
    return None


def find_bpmn_process(root: ET.Element) -> Union[ET.Element, None]:
    return find_unique_field(root, "process")


def find_lane_set(root: ET.Element) -> Union[ET.Element, None]:
    return find_unique_field(root, "laneSet")


def find_BPMN_plane(root: ET.Element) -> Union[ET.Element, None]:
    return find_unique_field(root, "BPMNPlane")


def find_element_by_id(root: ET.Element, id: str) -> Union[ET.Element, None]:
    for element in root.iter():
        if element.get("id") == id:
            return element
    return None


def find_bpmn_shape_by_bpmn_element(
    root: ET.Element, bpmn_element: str
) -> Union[ET.Element, None]:
    bpmn_plane = find_BPMN_plane(root)
    for element in bpmn_plane.iter():
        if (
            element.tag.endswith("BPMNShape")
            and element.get("bpmnElement") == bpmn_element
        ):
            return element

    return None


def find_bpmn_edge_by_bpmn_element(
    root: ET.Element, bpmn_element: str
) -> Union[ET.Element, None]:
    bpmn_plane = find_BPMN_plane(root)
    for element in bpmn_plane.iter():

        if (
            element.tag.endswith("BPMNEdge")
            and element.get("bpmnElement") == bpmn_element
        ):
            return element

    return None


def find_all_incoming_waypoints_for_task(task: ET.Element) -> List[str]:
    list_of_ids_of_sequence_flow = []
    for element in task.iter():
        if element.tag.endswith("incoming"):
            list_of_ids_of_sequence_flow.append(element.text)
    return list_of_ids_of_sequence_flow


def find_all_outgoing_waypoints_for_task(task: ET.Element) -> List[str]:
    list_of_ids_of_sequence_flow = []
    for element in task.iter():
        if element.tag.endswith("outgoing"):
            list_of_ids_of_sequence_flow.append(element.text)
    return list_of_ids_of_sequence_flow


def get_all_tasks(root: ET.Element) -> List[ET.Element]:
    tasks = []
    for element in root.iter():
        if element.tag.endswith("task"):
            tasks.append(element)
    return tasks


def get_task_role_map(
    dataframe: pd.DataFrame,
    task_field_name: str = "Activity",
    role_field_name: str = "Role",
) -> Dict[str, str]:
    task_to_role = {}
    for _, data in dataframe.iterrows():
        # space is not allowed within BPMN or xml fields, that is why spaces are replaced with underscores
        role_name = data[role_field_name].replace(" ", "_")
        task_to_role[data[task_field_name]] = role_name

    return task_to_role


def create_bounds_element(
    parent: ET.Element, x: float, y: float, width: float, height: float
) -> ET.Element:
    return ET.SubElement(
        parent,
        f"{{{NS['omgdc']}}}Bounds",
        {
            "x": str(x),
            "y": str(y),
            "width": str(width),
            "height": str(height),
        },
    )
