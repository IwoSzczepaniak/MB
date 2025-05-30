from utils import *


def parse_bpmn_file(bpmn_file_path: Union[str, None]) -> ET.ElementTree:
    if bpmn_file_path is None:
        bpmn_file_path = "input_diagram.bpmn"
    tree = ET.parse(bpmn_file_path)
    return tree


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


def convert_log_to_dataframe(log_path: str) -> pd.DataFrame:
    dataframe = pd.read_csv(log_path)
    return dataframe


def convert_log_to_bpmn(
    log_path,
    case_id_field_name,
    activity_field_name,
    timestamp_field_name,
    path_to_save_bpmn="input_diagram.bpmn",
) -> pd.DataFrame:
    dataframe = convert_log_to_dataframe(log_path)
    bpmn_model = create_bpmn_from_dataframe(
        dataframe, case_id_field_name, activity_field_name, timestamp_field_name
    )
    pm4py.write_bpmn(bpmn_model, path_to_save_bpmn)
    return dataframe


def add_roles_to_bpmn(
    root: ET.Element, task_to_role: Dict[str, str]
) -> Dict[str, float]:

    add_lane_set(root, "custom_laneSet")

    unique_roles = set(task_to_role.values())
    role_to_vertical_position = {}
    for role in unique_roles:
        lane = add_lane(root, role)
        _, y, bpmn_lane_id = add_lane_di(root, lane)
        role = find_element_by_id(root, bpmn_lane_id)
        role_to_vertical_position[role.get("name")] = y

    return role_to_vertical_position


def fix_tasks(
    root: ET.Element, role_to_vertical_position: Dict[str, float]
) -> Dict[str, float]:
    tasks = get_all_tasks(root)
    task_to_vertical_position = {}
    for task in tasks:
        task_id = task.get("id")
        task_name = task.get("name")

        bpmn_shape = find_bpmn_shape_by_bpmn_element(root, task_id)
        bounds = bpmn_shape.findall("omgdc:Bounds", NS)[0]
        bpmn_shape.remove(bounds)
        role = task_to_role[task_name]
        create_bounds_element(
            parent=bpmn_shape,
            x=float(bounds.get("x")),
            y=role_to_vertical_position[role] + LANE_HEIGHT // 2 - 18,
            width=float(bounds.get("width")),
            height=float(bounds.get("height")),
        )
        task_to_vertical_position[task] = (
            role_to_vertical_position[role] + LANE_HEIGHT // 2
        )

    return task_to_vertical_position


def fix_waypoints(
    root: ET.Element, task_to_vertical_position: Dict[ET.Element, float]
) -> None:
    tasks = get_all_tasks(root)

    for task in tasks:
        incoming = find_all_incoming_waypoints_for_task(task)
        outgoing = find_all_outgoing_waypoints_for_task(task)

        # x positions of waypoints are right, just their y need to be adjusted to their tasks
        proper_y = task_to_vertical_position[task]

        # for incoming arrows, only the y last pair of coordinates needs to be changed,
        for sequence_id in incoming:
            bpmn_edge = find_bpmn_edge_by_bpmn_element(tree.getroot(), sequence_id)
            positions = []
            elements = []
            for element in bpmn_edge.findall("ns6:waypoint", NS):
                elements.append(element)
                positions.append((float(element.get("x")), float(element.get("y"))))

            # removing all existing coordinates of waypoints
            for element in elements:
                bpmn_edge.remove(element)

            last_x, last_y = positions.pop(-1)
            positions.append((last_x, proper_y))
            for x, y in positions:
                ET.SubElement(
                    bpmn_edge,
                    f"{{{NS['ns6']}}}waypoint",
                    {
                        "x": str(x + 8),
                        "y": str(y),
                    },
                )

        # similar logic for outgoing, however here first y in first pair of coordinates needs to be adjusted
        for sequence_id in outgoing:
            bpmn_edge: ET.Element = find_bpmn_edge_by_bpmn_element(
                tree.getroot(), sequence_id
            )
            positions = []
            elements = []
            for element in bpmn_edge.findall("ns6:waypoint", NS):
                elements.append(element)
                positions.append((float(element.get("x")), float(element.get("y"))))

            for element in elements:
                bpmn_edge.remove(element)

            last_x, last_y = positions.pop(0)
            positions.insert(0, (last_x, proper_y))
            for x, y in positions:
                ET.SubElement(
                    bpmn_edge,
                    f"{{{NS['ns6']}}}waypoint",
                    {
                        "x": str(x),
                        "y": str(y),
                    },
                )


if __name__ == "__main__":

    bpmn_file_path = "input_diagram.bpmn"

    # ---------------------- repairExample.csv -----------------------

    role_field_name = "Resource"
    activity_field_name = "Activity"
    dataframe = convert_log_to_bpmn(
        log_path="example_logs/repairExample.csv",
        case_id_field_name="Case ID",
        activity_field_name="Activity",
        timestamp_field_name="Start Timestamp",
        path_to_save_bpmn=bpmn_file_path,
    )

    # ---------------------- purchasingExample.csv --------------------

    # role_field_name = "Role"
    # activity_field_name = "Activity"
    # dataframe = convert_log_to_bpmn(
    #     log_path="example_logs/purchasingExample.csv",
    #     case_id_field_name="Case ID",
    #     activity_field_name="Activity",
    #     timestamp_field_name="Start Timestamp",
    #     path_to_save_bpmn=bpmn_file_path,
    # )

    # ---------------------- new_teleclaims_changed_labels.csv --------------------

    # role_field_name = "resource"
    # activity_field_name = "action"  # alternatively task_field_name
    # dataframe = convert_log_to_bpmn(
    #     log_path="example_logs/new_teleclaims_changed_labels.csv",
    #     case_id_field_name="id",
    #     activity_field_name=activity_field_name,
    #     timestamp_field_name="from",
    #     path_to_save_bpmn=bpmn_file_path,
    # )

    tree = parse_bpmn_file(bpmn_file_path)

    task_to_role = get_task_role_map(
        dataframe, task_field_name=activity_field_name, role_field_name=role_field_name
    )
    role_to_vertical_position = add_roles_to_bpmn(tree.getroot(), task_to_role)
    task_to_vertical_position = fix_tasks(tree.getroot(), role_to_vertical_position)
    fix_waypoints(tree.getroot(), task_to_vertical_position)

    tree.write("output_diagram.bpmn", encoding="utf-8", xml_declaration=True)
