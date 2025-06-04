import { useState, useEffect, useRef, useCallback } from "react";
import Modeler from "bpmn-js/lib/Modeler";

const useBpmnModeler = (containerRef) => {
  const modelerRef = useRef(null);
  const [isReady, setIsReady] = useState(false);
  const [error, setError] = useState(null);

  const loadDiagram = useCallback(async (url) => {
    const modeler = modelerRef.current;
    if (!modeler) {
      console.warn("Modeler instance not available for loading diagram.");
      setError("Modeler instance not ready.");
      setIsReady(false);
      return;
    }

    try {
      console.log(`Fetching diagram from: ${url}`);
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(
          `HTTP error! status: ${response.status} loading ${url}`
        );
      }
      const initialXML = await response.text();
      console.log("Diagram XML fetched.");
      await modeler.importXML(initialXML);
      modeler.get("canvas").zoom("fit-viewport");
      console.log("Diagram loaded successfully.");
      setIsReady(true);
      setError(null);
    } catch (err) {
      console.error("Failed to load diagram:", err);
      setError(err.message);
      setIsReady(false);
    }
  }, []);

  useEffect(() => {
    if (!containerRef.current) {
      console.warn("Container ref is not available yet.");
      return;
    }

    if (!modelerRef.current) {
      const modeler = new Modeler({
        container: containerRef.current,
        keyboard: {
          bindTo: window,
        },
      });
      modelerRef.current = modeler;
      console.log("Bpmn Modeler initialized.");
    }

    return () => {
      if (modelerRef.current) {
        console.log("Destroying Bpmn Modeler instance.");
        modelerRef.current.destroy();
        modelerRef.current = null;
        setIsReady(false);
      }
    };
  }, [containerRef]);

  return { modeler: modelerRef.current, isReady, error, loadDiagram };
};

export default useBpmnModeler;
