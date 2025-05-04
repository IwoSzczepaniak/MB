const ErrorMessage = ({ message }) => {
  if (!message) return null;
  return (
    <div
      style={{
        color: "red",
        marginTop: "10px",
        padding: "10px",
        border: "1px solid red",
      }}
    >
      Error: {message}
    </div>
  );
};

export default ErrorMessage;
