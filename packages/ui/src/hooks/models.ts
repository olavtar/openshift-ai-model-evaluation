// This project was developed with assistance from AI tools.

import { useQuery } from '@tanstack/react-query';
import { getModels, getModelStatus } from '../services/models';

export function useModels() {
    return useQuery({
        queryKey: ['models'],
        queryFn: getModels,
    });
}

export function useModelStatus(modelId: number) {
    return useQuery({
        queryKey: ['model-status', modelId],
        queryFn: () => getModelStatus(modelId),
        refetchInterval: 30_000,
    });
}
