# Fronted displaying the BMPN diagram using bpmn.io
It uses react and vite.

It fetches the diagram from `frontend/public/diagram.bpmn`

## Running the project

### Manually:

#### Frontend
1.  Navigate to the `frontend` directory:
    ```bash
    cd frontend
    ```
2.  Install dependencies:
    ```bash
    npm install
    ```
3.  Run the development server:
    ```bash
    npm run dev
    ```

#### Backend
1. Navigate to the `backend` directory:
    ```bash
    cd backend
    ``` 
2.  Install dependencies:
    ```bash
    pipenv install
    pipenv shell
    ```
3.  Run the development server:
    ```bash
    python3 main.py
    ```

Using docker:
```bash
docker compose up
```


This will start the development server, typically accessible at `http://localhost:5173` (check the terminal output). 