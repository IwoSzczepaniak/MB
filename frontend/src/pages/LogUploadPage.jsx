import React, { useState } from 'react';

function LogUploadPage() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [diagramUrl, setDiagramUrl] = useState(null);

  const handleFileChange = (event) => {
    const file = event.target.files[0];
    if (file && file.type === 'text/csv') {
      setSelectedFile(file);
      setDiagramUrl(null); // Reset diagram URL when new file is selected
      setError(null); // Reset error
    } else {
      setSelectedFile(null);
      alert('Please select a CSV file.');
    }
  };

  const handleSubmit = async () => {
    if (selectedFile) {
      setIsLoading(true);
      setError(null);
      setDiagramUrl(null);

      const formData = new FormData();
      formData.append('csv_file', selectedFile); // Ensure the key matches backend: 'csv_file'

      try {
        const response = await fetch('http://localhost:8000/generate_bpmn/', {
          method: 'POST',
          body: formData,
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({ message: 'Failed to process file. Server error.' }));
          throw new Error(errorData.detail || errorData.message || `HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        console.log('Success:', data);
        setDiagramUrl(data.diagramUrl);
        alert('File processed successfully! Diagram is available.');
      } catch (err) {
        console.error('Error:', err);
        setError(err.message);
        alert(`Error processing file: ${err.message}`);
      } finally {
        setIsLoading(false);
      }
    } else {
      alert('Please select a file first.');
    }
  };

  return (
    <div>
      <h2>Upload Log CSV File</h2>
      <input type="file" accept=".csv" onChange={handleFileChange} />
      <button onClick={handleSubmit} disabled={!selectedFile || isLoading}>
        {isLoading ? 'Processing...' : 'Upload Logs'}
      </button>
      {selectedFile && <p>Selected file: {selectedFile.name}</p>}
      {error && <p style={{ color: 'red' }}>Error: {error}</p>}
      {diagramUrl && (
        <div>
          <p>Diagram generated successfully!</p>
          <a href={diagramUrl} target="_blank" rel="noopener noreferrer">
            View Diagram (diagram.bpmn)
          </a>
        </div>
      )}
    </div>
  );
}

export default LogUploadPage;