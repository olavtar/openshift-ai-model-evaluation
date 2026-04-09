// This project was developed with assistance from AI tools.

import {
    QuestionSetSchema,
    type QuestionSet,
    type QuestionSetItem,
} from '../schemas/question-set';
import { z } from 'zod';

export async function createQuestionSet(
    name: string,
    questions: QuestionSetItem[],
): Promise<QuestionSet> {
    const response = await fetch('/api/question-sets/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, questions }),
    });
    if (!response.ok) throw new Error('Failed to create question set');
    const data = await response.json();
    return QuestionSetSchema.parse(data);
}

export async function listQuestionSets(): Promise<QuestionSet[]> {
    const response = await fetch('/api/question-sets/');
    if (!response.ok) throw new Error('Failed to fetch question sets');
    const data = await response.json();
    return z.array(QuestionSetSchema).parse(data);
}

export async function deleteQuestionSet(id: number): Promise<void> {
    const response = await fetch(`/api/question-sets/${id}`, { method: 'DELETE' });
    if (!response.ok) throw new Error('Failed to delete question set');
}
