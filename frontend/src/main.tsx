/* @refresh reload */
import { render } from "solid-js/web";
import { ThemeProvider } from "~/context/theme";
import App from "./App";
import "./index.css";

const root = document.getElementById("root");
if (!root) {
  throw new Error("Missing #root");
}

render(
  () => (
    <ThemeProvider>
      <App />
    </ThemeProvider>
  ),
  root
);
