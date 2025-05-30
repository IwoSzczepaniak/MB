import xml.etree.ElementTree as ET
import pandas as pd
import pm4py
import os
from typing import Tuple, List, Union, Dict, Set

# Define namespaces for easier access
NS = {
    "bpmn": "http://www.omg.org/spec/BPMN/20100524/MODEL",
    "bpmndi": "http://www.omg.org/spec/BPMN/20100524/DI",
    "omgdc": "http://www.omg.org/spec/DD/20100524/DC",
    "ns6": "http://www.omg.org/spec/DD/20100524/DI",
}

LANE_HEIGHT = 200
INITIAL_LANE_HORIZONTAL_SHIFT_LEFT = 100
INITIAL_LANE_HORIZONTAL_SHIFT_RIGHT = 250
INITIAL_LANE_VERTICAL_SHIFT = 20


def parse_bpmn_file(bpmn_file_path: str) -> ET.ElementTree:
    tree = ET.parse(bpmn_file_path)
    return tree


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
) -> Tuple[Dict[str, str], Set[str]]:
    task_to_role = {}
    for _, data in dataframe.iterrows():
        # space is not allowed within BPMN or xml fields, that is why spaces are replaced with underscores
        role_name = data[role_field_name].replace(" ", "_")
        task_to_role[data[task_field_name]] = role_name

    return task_to_role, set(task_to_role.values())


def create_bpmn_from_dataframe(
    dataframe: pd.DataFrame,
    case_id_key: str = "Case ID",
    activity_key: str = "Activity",
    timestamp_key: str = "Timestamp",
) -> pm4py.BPMN:
    dataframe = pm4py.format_dataframe(
        dataframe,
        case_id=case_id_key,
        activity_key=activity_key,
        timestamp_key=timestamp_key,
    )
    event_log = pm4py.convert_to_event_log(dataframe)
    bpmn_model = pm4py.discover_bpmn_inductive(event_log)
    return bpmn_model


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


def convert_log_to_dataframe(log_path: str) -> pd.DataFrame:
    dataframe = pd.read_csv(log_path)
    return dataframe


def convert_log_to_bpmn(
    log_path,
    case_id_field_name,
    activity_field_name,
    timestamp_field_name,
    path_to_save_bpmn,
) -> pd.DataFrame:
    dataframe = convert_log_to_dataframe(log_path)
    bpmn_model = create_bpmn_from_dataframe(
        dataframe, case_id_field_name, activity_field_name, timestamp_field_name
    )
    pm4py.write_bpmn(bpmn_model, path_to_save_bpmn)
    return dataframe


def add_roles_to_bpmn(dataframe: pd.DataFrame):
    pass


if __name__ == "__main__":

    dataframe = convert_log_to_bpmn(
        "repairExample.csv",
        "Case ID",
        "Activity",
        "Start Timestamp",
        "input_diagram.bpmn",
    )

    tree = parse_bpmn_file("input_diagram.bpmn")

    add_roles_to_bpmn(dataframe)
    task_to_role, unqiue_roles = get_task_role_map(
        dataframe, role_field_name="Resource"
    )
    lane_set = add_lane_set(tree.getroot(), "Custom_laneset")
    role_position_map = {}
    for role in unqiue_roles:
        lane = add_lane(tree.getroot(), role)
        x, y, bpmn_lane_id = add_lane_di(tree.getroot(), lane)
        role = find_element_by_id(tree.getroot(), bpmn_lane_id)
        role_position_map[role.get("name")] = (x, y)

    tasks = get_all_tasks(tree.getroot())
    task_to_y_position = {}
    for task in tasks:
        task_id = task.get("id")
        task_name = task.get("name")
        bpmn_shape = find_bpmn_shape_by_bpmn_element(tree.getroot(), task_id)
        bounds = bpmn_shape.findall("omgdc:Bounds", NS)
        role = task_to_role[task_name]
        _, y = role_position_map[role]
        result = bounds[0]
        x = float(result.get("x"))
        width = float(result.get("width"))
        height = float(result.get("height"))
        bpmn_shape.remove(result)
        task_to_y_position[task] = y + LANE_HEIGHT // 2 - 18
        create_bounds_element(bpmn_shape, x, y + LANE_HEIGHT // 2 - 18, width, height)

    for task in tasks:
        incoming = find_all_incoming_waypoints_for_task(task)
        outgoing = find_all_outgoing_waypoints_for_task(task)

        y_position = task_to_y_position[task]

        for id in incoming:
            bpmn_edge = find_bpmn_edge_by_bpmn_element(tree.getroot(), id)
            positions = []
            elements = []
            for element in bpmn_edge.findall("ns6:waypoint", NS):
                print(element.get("x"))
                elements.append(element)
                positions.append((float(element.get("x")), float(element.get("y"))))

            for element in elements:
                bpmn_edge.remove(element)

            last_x, last_y = positions.pop(-1)
            positions.append((last_x, y_position))
            for x, y in positions:
                ET.SubElement(
                    bpmn_edge,
                    f"{{{NS['ns6']}}}waypoint",
                    {
                        "x": str(x),
                        "y": str(y),
                    },
                )

        for id in outgoing:
            bpmn_edge: ET.Element = find_bpmn_edge_by_bpmn_element(tree.getroot(), id)
            positions = []
            elements = []
            for element in bpmn_edge.findall("ns6:waypoint", NS):
                elements.append(element)
                positions.append((float(element.get("x")), float(element.get("y"))))

            for element in elements:
                bpmn_edge.remove(element)

            last_x, last_y = positions.pop(0)
            positions.insert(0, (last_x, y_position))
            for x, y in positions:
                ET.SubElement(
                    bpmn_edge,
                    f"{{{NS['ns6']}}}waypoint",
                    {
                        "x": str(x),
                        "y": str(y),
                    },
                )

    tree.write("output_diagram.xml", encoding="utf-8", xml_declaration=True)
