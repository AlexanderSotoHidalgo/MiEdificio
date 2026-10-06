import { defineConfig } from 'orval'

export default defineConfig({
  miedificio: {
    input: './openapi.json',
    output: {
      target: './src/api/generated/endpoints.ts',
      schemas: './src/api/generated/models',
      client: 'react-query',
      httpClient: 'axios',
      clean: true,
      override: {
        mutator: { path: './src/api/client.ts', name: 'orvalClient' },
      },
    },
  },
})
