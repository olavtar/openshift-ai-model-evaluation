// This project was developed with assistance from AI tools.

import { createFileRoute } from '@tanstack/react-router';
import { useRef, useState } from 'react';
import { useDocuments, useUploadDocument, useDeleteDocument } from '../../hooks/documents';
import { FileText, Upload, Trash2, Loader2, AlertCircle } from 'lucide-react';
import type { DocumentResponse } from '../../schemas/documents';
import { DOC_STATUS_COLORS } from '../../lib/status-colors';

export const Route = createFileRoute('/documents/')({
    component: DocumentsPage,
});

function formatFileSize(bytes: number | null | undefined): string {
    if (bytes == null) return '--';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function StatusBadge({ status }: { status: string }) {
    return (
        <span
            className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${DOC_STATUS_COLORS[status] ?? DOC_STATUS_COLORS.processing}`}
        >
            {status}
        </span>
    );
}

function DocumentRow({
    doc,
    onDelete,
    isDeleting,
}: {
    doc: DocumentResponse;
    onDelete: (id: number) => void;
    isDeleting: boolean;
}) {
    return (
        <div className="flex items-center justify-between rounded-lg border p-4">
            <div className="flex items-center gap-3">
                <FileText className="h-5 w-5 text-muted-foreground" />
                <div className="flex flex-col gap-1">
                    <div className="flex items-center gap-2">
                        <span className="font-medium">{doc.filename}</span>
                        <StatusBadge status={doc.status} />
                    </div>
                    <span className="text-xs text-muted-foreground">
                        {doc.chunk_count} chunks
                        {doc.page_count != null && ` -- ${doc.page_count} pages`}
                        {' -- '}
                        {formatFileSize(doc.file_size_bytes)}
                        {doc.created_at &&
                            ` -- ${new Date(doc.created_at).toLocaleDateString()}`}
                    </span>
                    {doc.error_message && (
                        <span className="flex items-center gap-1 text-xs text-destructive">
                            <AlertCircle className="h-3 w-3" />
                            {doc.error_message}
                        </span>
                    )}
                </div>
            </div>
            <button
                onClick={() => onDelete(doc.id)}
                disabled={isDeleting}
                className="rounded-lg p-2 text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive disabled:opacity-50"
                title="Delete document"
            >
                {isDeleting ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                    <Trash2 className="h-4 w-4" />
                )}
            </button>
        </div>
    );
}

function UploadForm({ onUploaded }: { onUploaded: () => void }) {
    const uploadMutation = useUploadDocument();
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [dragOver, setDragOver] = useState(false);

    const handleFile = (file: File) => {
        if (!file.name.toLowerCase().endsWith('.pdf')) {
            return;
        }
        uploadMutation.mutate(file, {
            onSuccess: () => {
                onUploaded();
                if (fileInputRef.current) fileInputRef.current.value = '';
            },
        });
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        setDragOver(false);
        const file = e.dataTransfer.files[0];
        if (file) handleFile(file);
    };

    return (
        <div className="rounded-xl border bg-card p-6">
            <h3 className="mb-4 text-lg font-semibold">Upload Document</h3>
            <div
                onDragOver={(e) => {
                    e.preventDefault();
                    setDragOver(true);
                }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleDrop}
                className={`flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 transition-colors ${
                    dragOver
                        ? 'border-primary bg-primary/5'
                        : 'border-muted-foreground/25'
                }`}
            >
                <Upload className="mb-2 h-8 w-8 text-muted-foreground" />
                <p className="mb-1 text-sm text-muted-foreground">
                    Drag and drop a PDF file here, or
                </p>
                <label className="cursor-pointer rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90">
                    Browse files
                    <input
                        ref={fileInputRef}
                        type="file"
                        accept=".pdf"
                        className="hidden"
                        onChange={(e) => {
                            const file = e.target.files?.[0];
                            if (file) handleFile(file);
                        }}
                    />
                </label>
                <p className="mt-2 text-xs text-muted-foreground">PDF files only, max 50 MB</p>
            </div>

            {uploadMutation.isPending && (
                <div className="mt-3 flex items-center gap-2 text-sm text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Uploading and processing...
                </div>
            )}

            {uploadMutation.isSuccess && (
                <p className="mt-3 text-sm text-emerald-600 dark:text-emerald-400">
                    {uploadMutation.data.message}
                </p>
            )}

            {uploadMutation.error && (
                <p className="mt-3 text-sm text-destructive">{uploadMutation.error.message}</p>
            )}
        </div>
    );
}

function DocumentsPage() {
    const { data: documents, isLoading, error, refetch } = useDocuments();
    const deleteMutation = useDeleteDocument();
    const [showUpload, setShowUpload] = useState(false);
    const [deletingId, setDeletingId] = useState<number | null>(null);

    const handleDelete = (id: number) => {
        setDeletingId(id);
        deleteMutation.mutate(id, {
            onSettled: () => setDeletingId(null),
        });
    };

    return (
        <div className="p-4 sm:p-6 lg:p-8">
            <div className="mx-auto max-w-5xl">
                <div className="mb-6 flex items-center justify-between">
                    <div>
                        <h1 className="text-2xl font-bold tracking-tight">Documents</h1>
                        <p className="text-sm text-muted-foreground">
                            Upload and manage PDF documents for RAG evaluation
                        </p>
                    </div>
                    <button
                        onClick={() => setShowUpload(!showUpload)}
                        className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
                    >
                        <Upload className="h-4 w-4" />
                        Upload
                    </button>
                </div>

                {showUpload && (
                    <div className="mb-6">
                        <UploadForm
                            onUploaded={() => {
                                refetch();
                            }}
                        />
                    </div>
                )}

                {isLoading && (
                    <p className="text-sm text-muted-foreground">Loading documents...</p>
                )}
                {error && <p className="text-sm text-destructive">{error.message}</p>}

                {documents && documents.length === 0 && !showUpload && (
                    <div className="rounded-xl border bg-card p-8 text-center">
                        <FileText className="mx-auto mb-3 h-8 w-8 text-muted-foreground" />
                        <p className="text-sm text-muted-foreground">
                            No documents yet. Click &quot;Upload&quot; to add a PDF.
                        </p>
                    </div>
                )}

                {documents && documents.length > 0 && (
                    <div className="space-y-3">
                        {documents.map((doc) => (
                            <DocumentRow
                                key={doc.id}
                                doc={doc}
                                onDelete={handleDelete}
                                isDeleting={deletingId === doc.id}
                            />
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
