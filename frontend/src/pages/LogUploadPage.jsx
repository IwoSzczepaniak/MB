import React, { useState } from 'react';

function LogUploadPage() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);

  const handleFileChange = (event) => {
    const file = event.target.files[0];
    if (file && file.type === 'text/csv') {
      setSelectedFile(file);
      setError(null);
      setSuccessMessage(null);
    } else {
      setSelectedFile(null);
      alert('Please select a CSV file.');
    }
  };

  const handleSubmit = async () => {
    if (selectedFile) {
      setIsLoading(true);
      setError(null);
      setSuccessMessage(null);

      const formData = new FormData();
      formData.append('csv_file', selectedFile);

      try {
        const response = await fetch('http://localhost:8000/generate_bpmn/', {
          method: 'POST',
          body: formData,
        });

        if (!response.ok) {
          let errorMsg = `HTTP error! status: ${response.status}`;
          try {
            const errorData = await response.json();
            errorMsg = errorData.detail || errorData.message || errorMsg;
          } catch (e) {
            errorMsg = response.statusText || errorMsg;
          }
          throw new Error(errorMsg);
        }

        const blob = await response.blob();
        const downloadUrl = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = downloadUrl;
        link.setAttribute('download', 'diagram.bpmn');
        document.body.appendChild(link);
        link.click();
        link.parentNode.removeChild(link);
        window.URL.revokeObjectURL(downloadUrl);

        setSuccessMessage('Diagram downloaded successfully!');
        alert('Diagram downloaded successfully!');

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
        {isLoading ? 'Processing...' : 'Upload & Download Diagram'}
      </button>
      {selectedFile && <p>Selected file: {selectedFile.name}</p>}
      {error && <p style={{ color: 'red' }}>Error: {error}</p>}
      {successMessage && <p style={{ color: 'green' }}>{successMessage}</p>}
    </div>
  );
}

export default LogUploadPage;
