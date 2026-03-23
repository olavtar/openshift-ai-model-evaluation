// This project was developed with assistance from AI tools.

import { useQuery, UseQueryResult } from '@tanstack/react-query';
import { getReadiness } from '../services/health';
import type { Readiness } from '../schemas/health';

export const useHealth = (): UseQueryResult<Readiness, Error> => {
    return useQuery({
        queryKey: ['health'],
        queryFn: getReadiness,
        refetchInterval: 30_000,
    });
};
