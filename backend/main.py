from utils import *
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import shutil
import os
import uuid
import random


STATIC_FILES_DIR = "generated_bpmns"
os.makedirs(STATIC_FILES_DIR, exist_ok=True)


def cleanup_all_static_bpmn_files():
    if os.path.exists(STATIC_FILES_DIR):
        for filename in os.listdir(STATIC_FILES_DIR):
            file_path = os.path.join(STATIC_FILES_DIR, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                    print(f"INFO: Deleted {file_path}.")
            except Exception as e:
                print(f"ERROR: Failed to delete {file_path}. Reason: {e}")
    else:
        print(f"INFO: Directory {STATIC_FILES_DIR} not found, no cleanup needed.")


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
    root: ET.Element,
    role_to_vertical_position: Dict[str, float],
    task_to_role: Dict[str, str],
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


def fix_starting_node(
    root: ET.Element, task_to_vertical_position: Dict[ET.Element, float]
) -> None:

    start_event = find_bpmn_start_event(root)
    bpmn_element = find_element_by_id(root, start_event.get("id"))
    find_bpmn_shape_by_bpmn_element(root, bpmn_element)

    tasks = task_to_vertical_position.keys()
    bpmn_shapes = [
        find_bpmn_shape_by_bpmn_element(root, task.get("id")) for task in tasks
    ]
    bounds_of_shapes = [shape.findall("omgdc:Bounds", NS)[0] for shape in bpmn_shapes]
    x = float("inf")
    right_y = float("inf")
    for bound in bounds_of_shapes:
        if float(bound.get("x")) < x:
            x = float(bound.get("x"))
            right_y = float(bound.get("y"))
    bpmn_shape = find_bpmn_shape_by_bpmn_element(root, bpmn_element.get("id"))
    bounds = bpmn_shape.findall("omgdc:Bounds", NS)[0]
    bpmn_shape.remove(bounds)
    create_bounds_element(
        parent=bpmn_shape,
        x=bounds.get("x"),
        y=right_y,
        width=bounds.get("width"),
        height=bounds.get("height"),
    )

    # outgoing_waypoints = bpmn_element.findall(f"{{{NS['bpmn']}}}outgoing", NS)
    # outgoing_waypoints_ids = [waypoint.text for waypoint in outgoing_waypoints]
    # bpmn_edges = [
    #     find_bpmn_edge_by_bpmn_element(root, waypoint_id)
    #     for waypoint_id in outgoing_waypoints_ids
    # ]

    # for bpmn_edge in bpmn_edges:
    #     positions = []
    #     elements = []
    #     for element in bpmn_edge.findall("ns6:waypoint", NS):
    #         elements.append(element)
    #         positions.append((float(element.get("x")), float(element.get("y"))))

    #     for element in elements:
    #         bpmn_edge.remove(element)

    #     last_x, last_y = positions.pop(0)
    #     positions = positions[-1:]
    #     positions.insert(0, (last_x, right_y + float(bounds.get("height")) / 2))
    #     for x, y in positions:
    #         ET.SubElement(
    #             bpmn_edge,
    #             f"{{{NS['ns6']}}}waypoint",
    #             {
    #                 "x": str(x),
    #                 "y": str(y),
    #             },
    #         )


def find_closest_left_task(root, tuples_of_positions_for_task, gateway_bounds):
    found_x = float("inf")
    found_y = float("inf")

    gateway_x = float(gateway_bounds.get("x"))
    gateway_y = float(gateway_bounds.get("y"))
    for x, y in tuples_of_positions_for_task:
        if abs(x - gateway_x) < abs(found_x - gateway_x):
            found_x = x
            found_y = y

    if found_y == float("inf"):
        start_event = find_bpmn_start_event(root)
        bpmn_shape = find_bpmn_shape_by_bpmn_element(root, start_event.get("id"))
        bounds = bpmn_shape.findall("omgdc:Bounds", NS)[0]
        found_x = bounds.get("x")
        found_y = bounds.get("y")

    return found_x, found_y


def fix_gateways(root: ET.Element, task_to_vertical_position):
    tasks = task_to_vertical_position.keys()

    bpmn_shapes = [
        find_bpmn_shape_by_bpmn_element(root, task.get("id")) for task in tasks
    ]

    bounds_of_shapes = [shape.findall("omgdc:Bounds", NS)[0] for shape in bpmn_shapes]
    tuples_of_positions_for_tasks = [
        (float(bounds.get("x")), float(bounds.get("y"))) for bounds in bounds_of_shapes
    ]

    gateways = []
    for item in root.iter():
        if item.tag.endswith("exclusiveGateway") or item.tag.endswith(
            "parallelGateway"
        ):
            gateways.append(item)

    positions = []
    gateway_shapes = []
    for gateway in gateways:
        gateway_shape = find_bpmn_shape_by_bpmn_element(root, gateway.get("id"))
        gateway_bounds = gateway_shape.findall("omgdc:Bounds", NS)[0]
        x, y = find_closest_left_task(
            root, tuples_of_positions_for_tasks, gateway_bounds
        )
        gateway_shapes.append(gateway_shape)
        positions.append((x, y))

    for gateway_shape, (desired_x, desired_y) in zip(gateway_shapes, positions):
        bounds = gateway_shape.findall("omgdc:Bounds", NS)[0]
        gateway_shape.remove(bounds)

        create_bounds_element(
            parent=gateway_shape,
            x=float(bounds.get("x")),
            y=desired_y,
            width=float(bounds.get("width")),
            height=float(bounds.get("height")),
        )


def fix_ending_node(
    root: ET.Element, task_to_vertical_position: Dict[ET.Element, float]
) -> None:

    start_event = find_bpmn_end_event(root)
    bpmn_element = find_element_by_id(root, start_event.get("id"))
    find_bpmn_shape_by_bpmn_element(root, bpmn_element)

    tasks = task_to_vertical_position.keys()
    bpmn_shapes = [
        find_bpmn_shape_by_bpmn_element(root, task.get("id")) for task in tasks
    ]
    bounds_of_shapes = [shape.findall("omgdc:Bounds", NS)[0] for shape in bpmn_shapes]
    x = -float("inf")
    right_y = float("inf")
    for bound in bounds_of_shapes:
        if float(bound.get("x")) > x:
            x = float(bound.get("x"))
            right_y = float(bound.get("y"))
    bpmn_shape = find_bpmn_shape_by_bpmn_element(root, bpmn_element.get("id"))
    bounds = bpmn_shape.findall("omgdc:Bounds", NS)[0]
    bpmn_shape.remove(bounds)
    create_bounds_element(
        parent=bpmn_shape,
        x=bounds.get("x"),
        y=right_y,
        width=bounds.get("width"),
        height=bounds.get("height"),
    )

    # incoming_waypoints = bpmn_element.findall(f"{{{NS['bpmn']}}}incoming", NS)
    # incoming_waypoints_ids = [waypoint.text for waypoint in incoming_waypoints]
    # bpmn_edges = [
    #     find_bpmn_edge_by_bpmn_element(root, waypoint_id)
    #     for waypoint_id in incoming_waypoints_ids
    # ]

    # for bpmn_edge in bpmn_edges:
    #     positions = []
    #     elements = []
    #     for element in bpmn_edge.findall("ns6:waypoint", NS):
    #         elements.append(element)
    #         positions.append((float(element.get("x")), float(element.get("y"))))

    #     for element in elements:
    #         bpmn_edge.remove(element)

    #     last_x, last_y = positions.pop(-1)
    #     positions = positions[:1]  # cutting all middlepoints to fix arrows
    #     positions.append((last_x, right_y + float(bounds.get("width")) / 2))
    #     for x, y in positions:
    #         ET.SubElement(
    #             bpmn_edge,
    #             f"{{{NS['ns6']}}}waypoint",
    #             {
    #                 "x": str(x),
    #                 "y": str(y),
    #             },
    #         )


def fix_overlaps(root):
    bpmn_plane = find_BPMN_plane(root)
    shapes = []
    for item in bpmn_plane.iter():
        if item.tag.endswith("BPMNShape") and not item.get("bpmnElement").startswith(
            "Lane"
        ):
            shapes.append(item)

    bounds_list = []
    for shape in shapes:
        bounds = shape.findall(f"omgdc:Bounds", NS)[0]
        bounds_list.append(bounds)

    possible_conflicts = []
    for shape, bounds in zip(shapes, bounds_list):
        possible_conflict = []
        for other_shape, other_bounds in zip(shapes, bounds_list):
            if (
                (
                    abs(float(bounds.get("x")) - float(other_bounds.get("x")))
                    < MAXIMUM_HORIZONTAL_DIFF_TO_FIX_LAYOUT
                )
            ) and (
                abs(float(bounds.get("y")) - float(other_bounds.get("y")))
                < MAXIMUM_VERTICAL_DIFF_TO_FIX_LAYOUT
            ):
                possible_conflict.append(other_shape)
        possible_conflict.append(shape)
        possible_conflicts.append(possible_conflict)
    possible_conflicts = [
        possible_conflict
        for possible_conflict in possible_conflicts
        if len(possible_conflict) > 1
    ]

    for possible_conflict in possible_conflicts:
        if len(possible_conflict) == 2:
            shape1 = possible_conflict[0]
            shape2 = possible_conflict[1]

            bounds1 = shape1.findall(f"{{{NS['omgdc']}}}Bounds")[0]
            bounds2 = shape2.findall(f"{{{NS['omgdc']}}}Bounds")[0]

            if shape1.get("id") == shape2.get("id"):
                continue

            # case already solved
            if (
                abs(float(bounds1.get("y")) - float(bounds2.get("y")))
                > MAXIMUM_VERTICAL_DIFF_TO_FIX_LAYOUT
            ):
                continue

            shape1.remove(bounds1)
            shape2.remove(bounds2)

            bigger_height = max(
                float(bounds1.get("height")), float(bounds2.get("height"))
            )

            create_bounds_element(
                parent=shape1,
                x=float(bounds1.get("x")),
                y=float(bounds1.get("y")) - LANE_HEIGHT / 4,
                width=float(bounds1.get("width")),
                height=float(bounds1.get("height")),
            )

            create_bounds_element(
                parent=shape2,
                x=float(bounds2.get("x")),
                y=float(bounds2.get("y")) + LANE_HEIGHT / 4,
                width=float(bounds2.get("width")),
                height=float(bounds2.get("height")),
            )

        if len(possible_conflict) == 3:
            shape1 = possible_conflict[0]
            shape2 = possible_conflict[1]
            shape3 = possible_conflict[2]

            bounds1 = shape1.findall(f"{{{NS['omgdc']}}}Bounds")[0]
            bounds2 = shape2.findall(f"{{{NS['omgdc']}}}Bounds")[0]
            bounds3 = shape3.findall(f"{{{NS['omgdc']}}}Bounds")[0]

            if (
                shape1.get("id") == shape2.get("id")
                or shape2.get("id") == shape3.get("id")
                or shape1.get("id") == shape3.get("id")
            ):
                continue

            # case already solved
            if (
                abs(float(bounds1.get("y")) - float(bounds2.get("y")))
                > MAXIMUM_VERTICAL_DIFF_TO_FIX_LAYOUT
            ):
                continue

            if (
                abs(float(bounds2.get("y")) - float(bounds3.get("y")))
                > MAXIMUM_VERTICAL_DIFF_TO_FIX_LAYOUT
            ):
                continue

            if (
                abs(float(bounds1.get("y")) - float(bounds3.get("y")))
                > MAXIMUM_VERTICAL_DIFF_TO_FIX_LAYOUT
            ):
                continue

            shape1.remove(bounds1)
            shape3.remove(bounds3)
            bigger_height = max(
                float(bounds1.get("height")),
                float(bounds2.get("height")),
                float(bounds3.get("height")),
            )

            create_bounds_element(
                parent=shape1,
                x=float(bounds1.get("x")),
                y=float(bounds1.get("y")) - bigger_height,
                width=float(bounds1.get("width")),
                height=float(bounds1.get("height")),
            )

            create_bounds_element(
                parent=shape3,
                x=float(bounds3.get("x")),
                y=float(bounds3.get("y")) + bigger_height,
                width=float(bounds3.get("width")),
                height=float(bounds3.get("height")),
            )


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
            bpmn_edge = find_bpmn_edge_by_bpmn_element(root, sequence_id)
            positions = []
            elements = []
            for element in bpmn_edge.findall("ns6:waypoint", NS):
                elements.append(element)
                positions.append((float(element.get("x")), float(element.get("y"))))

            # removing all existing coordinates of waypoints
            for element in elements:
                bpmn_edge.remove(element)

            last_x, last_y = positions.pop(-1)
            positions = positions[:1]  # cutting all middlepoints to fix arrows
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
            bpmn_edge: ET.Element = find_bpmn_edge_by_bpmn_element(root, sequence_id)
            positions = []
            elements = []
            for element in bpmn_edge.findall("ns6:waypoint", NS):
                elements.append(element)
                positions.append((float(element.get("x")), float(element.get("y"))))

            for element in elements:
                bpmn_edge.remove(element)

            last_x, last_y = positions.pop(0)
            positions = positions[-1:]
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


def fix_waypoints2(root):

    arrows = []
    for item in root.iter():
        if item.tag.endswith("sequenceFlow"):
            arrows.append(item)

    sources = []
    targets = []
    graphical_arrows = []
    for arrow in arrows:
        sources.append(find_bpmn_shape_by_bpmn_element(root, arrow.get("sourceRef")))
        targets.append(find_bpmn_shape_by_bpmn_element(root, arrow.get("targetRef")))
        graphical_arrows.append(find_bpmn_edge_by_bpmn_element(root, arrow.get("id")))

    for graphical_arrow, graphical_source, graphical_target in zip(
        graphical_arrows, sources, targets
    ):
        waypoints = graphical_arrow.findall(f"ns6:waypoint", NS)
        starting_point = waypoints[0]
        ending_point = waypoints[-1]

        for waypoint in waypoints:
            graphical_arrow.remove(waypoint)

        waypoints = [
            (float(waypoint.get("x")), float(waypoint.get("y")))
            for waypoint in waypoints
        ]

        source_bounds = graphical_source.find("omgdc:Bounds", NS)
        target_bounds = graphical_target.find("omgdc:Bounds", NS)

        source_x = float(source_bounds.get("x")) + float(source_bounds.get("width"))
        target_x = float(target_bounds.get("x"))

        source_y = (
            float(source_bounds.get("y")) + float(source_bounds.get("height")) / 2
        )
        target_y = (
            float(target_bounds.get("y")) + float(target_bounds.get("height")) / 2
        )

        start = (
            source_x,
            source_y,
        )
        end = (
            target_x,
            target_y,
        )

        new_waypoints = [start]
        random_shift = random.randint(
            -25, 15
        )  # random shift to avoid arrow overlapping
        random_bias = random.randint(1, 5)
        if abs(source_y - target_y) < 150:  # means they are in the same lane
            if abs(source_x - target_x) < 125:  # they are not far from each other
                new_waypoints.append(end)
            else:
                new_waypoints.append(
                    (source_x + random_bias, source_y - 80 + random_shift)
                )
                new_waypoints.append(
                    (target_x - random_bias, source_y - 80 + random_shift)
                )
                new_waypoints.append(end)
        else:  # nie sa w tym samym lanie
            if abs(source_x - target_x) < 125:  # they are not far from each other
                new_waypoints.append(end)
            else:
                if source_y - target_y > 0:  # koniec jest wyzej
                    new_waypoints.append(
                        (
                            source_x + random_bias,
                            source_y + 80 - abs(source_y - target_y) + random_shift,
                        )
                    )
                    new_waypoints.append(
                        (
                            target_x - random_bias,
                            source_y + 80 - abs(source_y - target_y) + random_shift,
                        )
                    )
                    new_waypoints.append(end)
                else:  # poczatek jest wyzej
                    new_waypoints.append(
                        (
                            source_x + random_bias,
                            source_y - 80 + abs(source_y - target_y) + random_shift,
                        )
                    )
                    new_waypoints.append(
                        (
                            target_x - random_bias,
                            source_y - 80 + abs(source_y - target_y) + random_shift,
                        )
                    )
                    new_waypoints.append(end)

        for x, y in new_waypoints:
            ET.SubElement(
                graphical_arrow,
                f"{{{NS['ns6']}}}waypoint",
                {
                    "x": str(x),
                    "y": str(y),
                },
            )


app = FastAPI()

origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://localhost:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)

app.mount(
    f"/{STATIC_FILES_DIR}", StaticFiles(directory=STATIC_FILES_DIR), name="static_files"
)


def run_bpmn_generation_logic(
    log_path: str,
    case_id_field_name: str,
    activity_field_name: str,
    timestamp_field_name: str,
    role_field_name: str,
    input_bpmn_path: str,
    output_bpmn_path: str,
):
    dataframe = convert_log_to_bpmn(
        log_path=log_path,
        case_id_field_name=case_id_field_name,
        activity_field_name=activity_field_name,
        timestamp_field_name=timestamp_field_name,
        path_to_save_bpmn=input_bpmn_path,
    )

    tree = parse_bpmn_file(input_bpmn_path)
    root = tree.getroot()

    task_to_role = get_task_role_map(
        dataframe, task_field_name=activity_field_name, role_field_name=role_field_name
    )
    role_to_vertical_position = add_roles_to_bpmn(root, task_to_role)
    task_to_vertical_position = fix_tasks(root, role_to_vertical_position, task_to_role)
    fix_starting_node(root, task_to_vertical_position)
    fix_ending_node(root, task_to_vertical_position)
    fix_gateways(root, task_to_vertical_position)
    fix_overlaps(root)
    fix_waypoints2(root)

    tree.write(output_bpmn_path, encoding="utf-8", xml_declaration=True)
    return dataframe


if __name__ == "__main__":
    run_bpmn_generation_logic(
        log_path="../example_logs/new_teleclaims_changed_labels.csv",
        case_id_field_name="id",
        activity_field_name="action",
        timestamp_field_name="from",
        role_field_name="resource",
        input_bpmn_path="input.bpmn",
        output_bpmn_path="output.bpmn",
    )

# @app.post("/generate_bpmn/")
# async def generate_bpmn_api(
#     csv_file: UploadFile = File(...),
#     role_field_name: str = Form("Resource"),
#     activity_field_name: str = Form("Activity"),
#     case_id_field_name: str = Form("Case ID"),
#     timestamp_field_name: str = Form("Start Timestamp"),
# ):
#     cleanup_all_static_bpmn_files()

#     temp_csv_path = f"temp_{csv_file.filename}"

#     unique_filename = f"{uuid.uuid4()}.bpmn"
#     output_bpmn_path = os.path.join(STATIC_FILES_DIR, unique_filename)

#     with open(temp_csv_path, "wb") as buffer:
#         shutil.copyfileobj(csv_file.file, buffer)

#     temp_input_bpmn_path = f"temp_input_{uuid.uuid4()}.bpmn"

#     try:
#         run_bpmn_generation_logic(
#             log_path=temp_csv_path,
#             case_id_field_name=case_id_field_name,
#             activity_field_name=activity_field_name,
#             timestamp_field_name=timestamp_field_name,
#             role_field_name=role_field_name,
#             input_bpmn_path=temp_input_bpmn_path,
#             output_bpmn_path=output_bpmn_path,
#         )

#         file_url = f"http://localhost:8000/{STATIC_FILES_DIR}/{unique_filename}"
#         return JSONResponse(content={"diagram_url": file_url})

#     finally:
#         if os.path.exists(temp_csv_path):
#             os.remove(temp_csv_path)
#         if os.path.exists(temp_input_bpmn_path):
#             os.remove(temp_input_bpmn_path)


# if __name__ == "__main__":
#     uvicorn.run(app, host="0.0.0.0", port=8000)
