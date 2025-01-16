import React from 'react';
import { ThemeProvider, CssBaseline, Container, AppBar, Toolbar, Button, Box } from '@mui/material';
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import { theme } from './theme';
import VideoUpload from './pages/VideoUpload';
import StreamVideo from './pages/StreamVideo';

function App() {
  return (
    <BrowserRouter>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <AppBar position="static">
          <Toolbar>
            <Box sx={{ flexGrow: 1 }}>
              <Button color="inherit" component={Link} to="/">
                Video Upload
              </Button>
              <Button color="inherit" component={Link} to="/stream">
                Stream Video
              </Button>
            </Box>
          </Toolbar>
        </AppBar>
        <Container maxWidth={false} sx={{ width: "60vw" }}>
          <Routes>
            <Route path="/" element={<VideoUpload />} />
            <Route path="/stream" element={<StreamVideo />} />
          </Routes>
        </Container>
      </ThemeProvider>
    </BrowserRouter>
  );
}

export default App;