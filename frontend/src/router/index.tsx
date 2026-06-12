import { createBrowserRouter } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { ChatPage } from '@/features/chat/ChatPage';
import { IngestPage } from '@/features/ingest/IngestPage';
import { DocumentsPage } from '@/features/documents/DocumentsPage';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    children: [
      { index: true, element: <ChatPage /> },
      { path: 'ingest', element: <IngestPage /> },
      { path: 'documents', element: <DocumentsPage /> },
    ],
  },
]);
