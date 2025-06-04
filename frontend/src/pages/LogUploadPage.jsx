import React, { useState } from 'react';

function LogUploadPage() {
  const [selectedFile, setSelectedFile] = useState(null);

  const handleFileChange = (event) => {
    const file = event.target.files[0];
    if (file && file.type === 'text/csv') {
      setSelectedFile(file);
    } else {
      setSelectedFile(null);
      alert('Please select a CSV file.');
    }
  };

  const handleSubmit = () => {
    if (selectedFile) {
      // For now, we'll just log the file info to the console
      // In the future, this is where the API call to send the file would go
      console.log('Selected file:', selectedFile);
      alert('File selected and ready for processing (not sent to API yet).');
      // Here you would typically use FormData to prepare the file for sending:
      // const formData = new FormData();
      // formData.append('logFile', selectedFile);
      // And then make a fetch or axios call, e.g.:
      // fetch('/api/upload-logs', { method: 'POST', body: formData })
      //   .then(response => response.json())
      //   .then(data => console.log('Success:', data))
      //   .catch(error => console.error('Error:', error));
    } else {
      alert('Please select a file first.');
    }
  };

  return (
    <div>
      <h2>Upload Log CSV File</h2>
      <input type="file" accept=".csv" onChange={handleFileChange} />
      <button onClick={handleSubmit} disabled={!selectedFile}>
        Upload Logs
      </button>
      {selectedFile && <p>Selected file: {selectedFile.name}</p>}
    </div>
  );
}

export default LogUploadPage; 