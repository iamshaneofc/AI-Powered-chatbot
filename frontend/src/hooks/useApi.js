import { useMutation, useQuery } from '@tanstack/react-query';
import { uploadDocument, uploadMedia, sendChat, fetchSummary } from '../services/api';

export const useUploadDocument = () => {
  return useMutation({
    mutationFn: uploadDocument,
  });
};

export const useUploadMedia = () => {
  return useMutation({
    mutationFn: uploadMedia,
  });
};

export const useChatQuery = () => {
  return useMutation({
    mutationFn: sendChat,
  });
};

export const useSummarize = (filename) => {
  return useQuery({
    queryKey: ['summary', filename],
    queryFn: () => fetchSummary(filename),
    enabled: !!filename,
  });
};
