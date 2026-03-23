// This project was developed with assistance from AI tools.

import { ModelSchema, ModelStatusSchema, type Model, type ModelStatus } from '../schemas/models';
import { z } from 'zod';

export const getModels = async (): Promise<Model[]> => {
    const response = await fetch('/api/models/');
    if (!response.ok) {
        throw new Error('Failed to fetch models');
    }
    const data = await response.json();
    return z.array(ModelSchema).parse(data);
};

export const getModelStatus = async (modelId: number): Promise<ModelStatus> => {
    const response = await fetch(`/api/models/${modelId}/status`);
    if (!response.ok) {
        throw new Error('Failed to fetch model status');
    }
    const data = await response.json();
    return ModelStatusSchema.parse(data);
};
