# Configuration

This project can be run with Node or Docker. Both methods are outlined below.

## Dockerization

To run this project using Docker, follow these steps:

1. Navigate to the project's root directory in your terminal.
2. Run the following command to build the Docker image: `docker build --build-arg VITE_API_URL=<your-api-url> --build-arg VITE_WS_URL=<your-ws-url> . -t f1-frontend ./frontend`
3. Run the following command to run the container: `docker run --rm -p <your-local-port>:80 f1-frontend`
4. Access the application at `http://localhost:<your-local-port>`.

## Development

To run this project locally, follow these steps:

1. Clone the repository: `git clone <repository-url>`
2. Navigate to the project's frontend directory: `cd <project-directory>/frontend`
3. Install dependencies: `npm install`
4. Start the development server: `npm run dev`
4. Access the application at the URL given by Vite, usually `http://localhost:5173`.

# React + TypeScript + Vite

This template provides a minimal setup to get React working in Vite with HMR and some Oxlint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the Oxlint configuration

If you are developing a production application, we recommend enabling type-aware lint rules by installing `oxlint-tsgolint` and editing `.oxlintrc.json`:

```json
{
  "$schema": "./node_modules/oxlint/configuration_schema.json",
  "plugins": ["react", "typescript", "oxc"],
  "options": {
    "typeAware": true
  },
  "rules": {
    "react/rules-of-hooks": "error",
    "react/only-export-components": ["warn", { "allowConstantExport": true }]
  }
}
```

See the [Oxlint rules documentation](https://oxc.rs/docs/guide/usage/linter/rules) for the full list of rules and categories.
