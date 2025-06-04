from utils import *
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import shutil
import os


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
    root: ET.Element, role_to_vertical_position: Dict[str, float], task_to_role: Dict[str, str]
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
                root, sequence_id
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


app = FastAPI()

origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
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
    fix_waypoints(root, task_to_vertical_position)

    tree.write(output_bpmn_path, encoding="utf-8", xml_declaration=True)
    return dataframe


@app.post("/generate_bpmn/")
async def generate_bpmn_api(
    csv_file: UploadFile = File(...),
    role_field_name: str = Form("Resource"),
    activity_field_name: str = Form("Activity"),
    case_id_field_name: str = Form("Case ID"),
    timestamp_field_name: str = Form("Start Timestamp"),
):
    temp_csv_path = f"temp_{csv_file.filename}"
    temp_output_bpmn_path = f"temp_output_{csv_file.filename}.bpmn"

    with open(temp_csv_path, "wb") as buffer:
        shutil.copyfileobj(csv_file.file, buffer)

    input_bpmn_path = "input_diagram.bpmn"

    try:
        run_bpmn_generation_logic(
            log_path=temp_csv_path,
            case_id_field_name=case_id_field_name,
            activity_field_name=activity_field_name,
            timestamp_field_name=timestamp_field_name,
            role_field_name=role_field_name,
            input_bpmn_path=input_bpmn_path,
            output_bpmn_path=temp_output_bpmn_path,
        )

        return FileResponse(
            path=temp_output_bpmn_path,
            media_type='application/octet-stream',
            filename='diagram.bpmn',
        )
    finally:
        if os.path.exists(temp_csv_path):
            os.remove(temp_csv_path)
        if os.path.exists(input_bpmn_path):
            os.remove(input_bpmn_path)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
