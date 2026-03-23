// This project was developed with assistance from AI tools.

import { z } from 'zod';

export const ModelSchema = z.object({
    id: z.number(),
    name: z.string(),
    endpoint_url: z.string(),
    deployment_mode: z.string(),
    is_active: z.boolean(),
});

export const ModelStatusSchema = z.object({
    name: z.string(),
    status: z.string(),
    deployment_mode: z.string(),
    endpoint_url: z.string(),
});

export type Model = z.infer<typeof ModelSchema>;
export type ModelStatus = z.infer<typeof ModelStatusSchema>;
