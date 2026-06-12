import type { IngestResponse, JobStatus } from '@/types';
import { baseApi } from './baseApi';

interface IngestRequest {
  directory: string;
  patterns?: string[];
  chunk_size?: number;
  overlap?: number;
}

export const ingestApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    ingestLocal: builder.mutation<IngestResponse, IngestRequest>({
      query: (body) => ({
        url: '/ingest/local',
        method: 'POST',
        body,
      }),
    }),
    uploadFiles: builder.mutation<IngestResponse, FormData>({
      query: (formData) => ({
        url: '/ingest/upload',
        method: 'POST',
        body: formData,
        // Do NOT set Content-Type — fetch sets it automatically with the multipart boundary.
        formData: true,
      }),
    }),
    getJobStatus: builder.query<JobStatus, string>({
      query: (jobId) => `/ingest/jobs/${jobId}`,
      providesTags: (_result, _error, jobId) => [{ type: 'Job', id: jobId }],
    }),
  }),
});

export const { useIngestLocalMutation, useUploadFilesMutation, useGetJobStatusQuery } = ingestApi;
