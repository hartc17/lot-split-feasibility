import { createTheme } from '@mui/material/styles';

export default createTheme({
  palette: {
    background: { default: '#f1f5f9' },
    primary: { main: '#2563eb' },
  },
  typography: {
    fontFamily: [
      '-apple-system',
      'BlinkMacSystemFont',
      '"Segoe UI"',
      'sans-serif',
    ].join(','),
    fontSize: 13,
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        'html, body, #root': { height: '100%' },
      },
    },
    MuiButton: {
      defaultProps: { size: 'small' },
      styleOverrides: {
        root: { textTransform: 'none', fontWeight: 500 },
      },
    },
    MuiTextField: {
      defaultProps: { size: 'small' },
    },
  },
});
