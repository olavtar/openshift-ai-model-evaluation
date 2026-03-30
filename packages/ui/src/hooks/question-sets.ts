// This project was developed with assistance from AI tools.

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listQuestionSets, createQuestionSet, deleteQuestionSet } from '../services/question-sets';

export function useQuestionSets() {
    return useQuery({
        queryKey: ['question-sets'],
        queryFn: listQuestionSets,
    });
}

export function useCreateQuestionSet() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ name, questions }: { name: string; questions: string[] }) =>
            createQuestionSet(name, questions),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['question-sets'] });
        },
    });
}

export function useDeleteQuestionSet() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (id: number) => deleteQuestionSet(id),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['question-sets'] });
        },
    });
}
