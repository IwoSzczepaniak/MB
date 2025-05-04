import React, { useEffect, useRef, useCallback } from "react";

import "bpmn-js/dist/assets/diagram-js.css";
import "bpmn-js/dist/assets/bpmn-font/css/bpmn.css";

import "./App.css";
import useBpmnModeler from "./hooks/useBpmnModeler";
import ErrorMessage from "./ErrorMessage";

function BpmnCanvas() {
  const canvasRef = useRef(null);

  const { modeler, isReady, error } = useBpmnModeler(canvasRef);

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

  return (
    <div className="App">
      <h1>BPMN Layer Adder (React)</h1>

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
