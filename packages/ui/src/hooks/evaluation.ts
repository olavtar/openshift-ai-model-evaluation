// This project was developed with assistance from AI tools.

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
    listEvalRuns,
    getEvalRun,
    createEvalRun,
    deleteEvalRun,
    rerunEval,
    compareEvalRuns,
    synthesizeQuestions,
} from '../services/evaluation';

export function useEvalRuns() {
    return useQuery({
        queryKey: ['eval-runs'],
        queryFn: listEvalRuns,
    });
}

export function useEvalRun(id: number) {
    return useQuery({
        queryKey: ['eval-run', id],
        queryFn: () => getEvalRun(id),
        refetchInterval: (query) => {
            const status = query.state.data?.status;
            return status === 'pending' || status === 'running' ? 3000 : false;
        },
    });
}

export function useCreateEvalRun() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ modelName, questions }: { modelName: string; questions: string[] }) =>
            createEvalRun(modelName, questions),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['eval-runs'] });
        },
    });
}

export function useDeleteEvalRun() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (id: number) => deleteEvalRun(id),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['eval-runs'] });
        },
    });
}

export function useRerunEval() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ evalRunId, modelName }: { evalRunId: number; modelName: string }) =>
            rerunEval(evalRunId, modelName),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['eval-runs'] });
        },
    });
}

export function useCompareEvalRuns(runAId: number, runBId: number) {
    return useQuery({
        queryKey: ['eval-compare', runAId, runBId],
        queryFn: () => compareEvalRuns(runAId, runBId),
        enabled: runAId > 0 && runBId > 0,
    });
}

export function useSynthesizeQuestions() {
    return useMutation({
        mutationFn: ({
            maxQuestions,
            documentIds,
        }: {
            maxQuestions?: number;
            documentIds?: number[];
        }) => synthesizeQuestions(maxQuestions, documentIds),
    });
}
