// This project was developed with assistance from AI tools.

import { z } from 'zod';

export const QuestionSetSchema = z.object({
    id: z.number(),
    name: z.string(),
    questions: z.array(z.string()),
    created_at: z.string().nullable().optional(),
});

export type QuestionSet = z.infer<typeof QuestionSetSchema>;
