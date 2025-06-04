import React, { useState } from 'react';
import './LogUploadPage.css'; // Import the CSS file

function LogUploadPage() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);

  const [roleFieldName, setRoleFieldName] = useState('Resource');
  const [activityFieldName, setActivityFieldName] = useState('Activity');
  const [caseIdFieldName, setCaseIdFieldName] = useState('Case ID');
  const [timestampFieldName, setTimestampFieldName] = useState('Start Timestamp');

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
      formData.append('role_field_name', roleFieldName);
      formData.append('activity_field_name', activityFieldName);
      formData.append('case_id_field_name', caseIdFieldName);
      formData.append('timestamp_field_name', timestampFieldName);

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
    <div className="page-container">
      <h2>Upload Log CSV File & Configure Parameters</h2>
      
      <div className="input-group">
        <label htmlFor="csvFile" className="label">CSV File:</label>
        <input id="csvFile" type="file" accept=".csv" onChange={handleFileChange} className="file-input-field" />
      </div>

      <fieldset className="config-fieldset">
        <legend className="config-legend">Field Name Configuration</legend>
        <div className="input-group">
          <label htmlFor="roleField" className="label">Role Field Name:</label>
          <input 
            id="roleField" 
            type="text" 
            value={roleFieldName} 
            onChange={(e) => setRoleFieldName(e.target.value)} 
            className="input-field"
          />
        </div>
        <div className="input-group">
          <label htmlFor="activityField" className="label">Activity Field Name:</label>
          <input 
            id="activityField" 
            type="text" 
            value={activityFieldName} 
            onChange={(e) => setActivityFieldName(e.target.value)} 
            className="input-field"
          />
        </div>
        <div className="input-group">
          <label htmlFor="caseIdField" className="label">Case ID Field Name:</label>
          <input 
            id="caseIdField" 
            type="text" 
            value={caseIdFieldName} 
            onChange={(e) => setCaseIdFieldName(e.target.value)} 
            className="input-field"
          />
        </div>
        <div className="input-group">
          <label htmlFor="timestampField" className="label">Timestamp Field Name:</label>
          <input 
            id="timestampField" 
            type="text" 
            value={timestampFieldName} 
            onChange={(e) => setTimestampFieldName(e.target.value)} 
            className="input-field"
          />
        </div>
      </fieldset>
      
      <button 
        onClick={handleSubmit} 
        disabled={!selectedFile || isLoading} 
        className="button"
      >
        {isLoading ? 'Processing...' : 'Upload & Download Diagram'}
      </button>
      
      {selectedFile && <p className="status-message">Selected file: {selectedFile.name}</p>}
      {error && <p className="error-message">Error: {error}</p>}
      {successMessage && <p className="success-message">{successMessage}</p>}
    </div>
  );
}

export default LogUploadPage;
