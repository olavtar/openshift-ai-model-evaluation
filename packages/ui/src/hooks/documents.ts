// This project was developed with assistance from AI tools.

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
    listDocuments,
    getDocument,
    uploadDocument,
    ingestFromUrl,
    deleteDocument,
} from '../services/documents';

export function useDocuments() {
    return useQuery({
        queryKey: ['documents'],
        queryFn: listDocuments,
    });
}

export function useDocument(id: number) {
    return useQuery({
        queryKey: ['document', id],
        queryFn: () => getDocument(id),
        refetchInterval: (query) => {
            const status = query.state.data?.status;
            return status === 'processing' ? 3000 : false;
        },
    });
}

export function useUploadDocument() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (file: File) => uploadDocument(file),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['documents'] });
        },
    });
}

export function useIngestFromUrl() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (url: string) => ingestFromUrl(url),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['documents'] });
        },
    });
}

export function useDeleteDocument() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (id: number) => deleteDocument(id),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['documents'] });
        },
    });
}
