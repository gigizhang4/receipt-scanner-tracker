import { useState } from 'react';
import { Box, Button, Container, Paper, Typography, CircularProgress } from '@mui/material';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import axios from 'axios';

function App() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);
    
    setLoading(true);
    try {
      const response = await axios.post('http://localhost:8080/scan-receipt', formData);
      setResult(response.data);
    } catch (error) {
      console.error('Error uploading receipt:', error);
    }
    setLoading(false);
  };

  return (
    <Container maxWidth="sm">
      <Box sx={{ my: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Receipt Scanner
        </Typography>
        
        <Paper sx={{ p: 3, textAlign: 'center' }}>
          <input
            accept="image/*"
            style={{ display: 'none' }}
            id="receipt-upload"
            type="file"
            onChange={handleFileUpload}
          />
          <label htmlFor="receipt-upload">
            <Button
              variant="contained"
              component="span"
              startIcon={<UploadFileIcon />}
              disabled={loading}
            >
              Upload Receipt
            </Button>
          </label>

          {loading && (
            <Box sx={{ mt: 2 }}>
              <CircularProgress />
            </Box>
          )}

          {result && (
            <Box sx={{ mt: 3, textAlign: 'left' }}>
              <Typography variant="h6">Results:</Typography>
              <Typography>Total: ${result.total}</Typography>
              <Typography>Date: {result.date}</Typography>
              <Typography variant="h6" sx={{ mt: 2 }}>Items:</Typography>
              {result.items.map((item, index) => (
                <Typography key={index}>
                  {item.name}: ${item.price}
                </Typography>
              ))}
            </Box>
          )}
        </Paper>
      </Box>
    </Container>
  );
}

export default App;
