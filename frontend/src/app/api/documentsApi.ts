import type { DocumentsResponse } from '@/types';
import { baseApi } from './baseApi';

export const documentsApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    listDocuments: builder.query<DocumentsResponse, void>({
      query: () => '/documents',
      providesTags: ['Document'],
    }),
    deleteDocument: builder.mutation<{ deleted_chunks: number; source_path: string }, string>({
      query: (sourcePath) => ({
        url: `/documents/${encodeURIComponent(sourcePath)}`,
        method: 'DELETE',
      }),
      invalidatesTags: ['Document'],
    }),
  }),
});

export const { useListDocumentsQuery, useDeleteDocumentMutation } = documentsApi;
