import { useCallback, useEffect, useState } from 'react'
import { errorMessage } from './api'

export function useResource<T>(key: string, load: (signal: AbortSignal) => Promise<T>) {
  const [revision, setRevision] = useState(0)
  const reload = useCallback(() => setRevision((value) => value + 1), [])
  const requestKey = `${key}:${revision}`
  const [result, setResult] = useState<{ key: string; data?: T; error?: string }>({ key: '' })
  useEffect(() => {
    const controller = new AbortController()
    load(controller.signal)
      .then((data) => { if (!controller.signal.aborted) setResult({ key: requestKey, data }) })
      .catch((error: unknown) => { if (!controller.signal.aborted) setResult({ key: requestKey, error: errorMessage(error) }) })
    return () => controller.abort()
  }, [load, requestKey])
  return {
    data: result.key === requestKey ? result.data : undefined,
    error: result.key === requestKey ? result.error : undefined,
    loading: result.key !== requestKey,
    reload,
  }
}
