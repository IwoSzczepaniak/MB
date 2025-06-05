import React, { useEffect, useRef, useCallback } from "react";
import { useLocation } from 'react-router-dom';

import "bpmn-js/dist/assets/diagram-js.css";
import "bpmn-js/dist/assets/bpmn-font/css/bpmn.css";

import "./App.css";
import useBpmnModeler from "./hooks/useBpmnModeler";
import ErrorMessage from "./ErrorMessage";

function BpmnCanvas() {
  const canvasRef = useRef(null);
  const location = useLocation();

  const { modeler, isReady, error, loadDiagram } = useBpmnModeler(canvasRef);

  const addHierarchicalLayers = useCallback(() => {
    if (!modeler) {
      console.warn("Modeler not available.");
      return;
    }
    console.log("Adding hierarchical layers - TO IMPLEMENT");
  }, [modeler]);

  useEffect(() => {
    if (error) {
      alert(`Failed to load diagram: ${error}`);
    }
  }, [error]);

  useEffect(() => {
    const diagramUrlFromState = location.state?.diagram_url;
    if (diagramUrlFromState && loadDiagram && typeof loadDiagram === 'function') {
      console.log("BpmnCanvas: Received diagram URL from state:", diagramUrlFromState);
      loadDiagram(diagramUrlFromState);
    } else if (location.state && !diagramUrlFromState) {
      console.warn("BpmnCanvas: Navigated with state, but diagram_url is missing.");
    }
  }, [location.state, loadDiagram]);

  return (
    <div className="App">
      <h1>BPMN Canvas</h1>

      <div
        className="canvasContainer"
        ref={canvasRef}
        style={{ height: "600px", border: "1px solid #ccc" }}
      />
      {error && (
        <ErrorMessage
          message={`Loading diagram failed: ${error}`}
        />
      )}
      <div className="controls">
        <button onClick={addHierarchicalLayers} disabled={!isReady}>
          Add Layers
        </button>
      </div>
    </div>
  );
}

export default BpmnCanvas;
