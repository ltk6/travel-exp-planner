import { z } from "zod";

const serverSchema = z.object({
  BACKEND_URL: z.string().url().default("http://localhost:5000"),
  INTERNAL_API_KEY: z.string().default(""),
  BACKEND_TIMEOUT_MS: z.coerce.number().int().positive().default(120000),
});

export const env = serverSchema.parse({
  BACKEND_URL: process.env.BACKEND_URL,
  INTERNAL_API_KEY: process.env.INTERNAL_API_KEY,
  BACKEND_TIMEOUT_MS: process.env.BACKEND_TIMEOUT_MS,
});
