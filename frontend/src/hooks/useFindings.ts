import { useState, useEffect } from 'react';
import api from '../lib/api';

interface Finding {
  id: number;
  file_path: string;
  line_start: number;
  severity: string;
  category: string;
  message: string;
  suggestion: string;
  confidence: number;
}

export function useFindings(prId: number) {
  const [findings, setFindings] = useState<Finding[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get(`/prs/${prId}/findings`).then((res) => {
      setFindings(res.data.findings || []);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [prId]);

  return { findings, loading };
}
