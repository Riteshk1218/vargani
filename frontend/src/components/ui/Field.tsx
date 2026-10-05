import { forwardRef, useId, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes, type TextareaHTMLAttributes } from 'react'
import { cn } from '../../utils/cn'

const CONTROL =
  'block w-full rounded-lg border-0 bg-white px-3 py-2 text-sm text-slate-900 ring-1 ring-inset ring-slate-300 placeholder:text-slate-400 focus:ring-2 focus:ring-inset focus:ring-brand-600 disabled:bg-slate-100'

interface FieldProps {
  label: string
  error?: string
  hint?: string
  required?: boolean
  children: (id: string, describedBy?: string) => ReactNode
  className?: string
}

export function Field({ label, error, hint, required, children, className }: FieldProps) {
  const id = useId()
  const describedBy = error ? `${id}-error` : hint ? `${id}-hint` : undefined
  return (
    <div className={cn('space-y-1', className)}>
      <label htmlFor={id} className="block text-sm font-medium text-slate-700">
        {label}
        {required && <span className="text-red-600"> *</span>}
      </label>
      {children(id, describedBy)}
      {error ? (
        <p id={`${id}-error`} className="text-sm text-red-600">
          {error}
        </p>
      ) : hint ? (
        <p id={`${id}-hint`} className="text-xs text-slate-500">
          {hint}
        </p>
      ) : null}
    </div>
  )
}

type InputProps = InputHTMLAttributes<HTMLInputElement> & { label: string; error?: string; hint?: string }

export const TextInput = forwardRef<HTMLInputElement, InputProps>(function TextInput({ label, error, hint, required, className, ...props }, ref) {
  return (
    <Field label={label} error={error} hint={hint} required={required} className={className}>
      {(id, describedBy) => (
        <input
          ref={ref}
          id={id}
          aria-invalid={Boolean(error)}
          aria-describedby={describedBy}
          className={cn(CONTROL, error && 'ring-red-500')}
          {...props}
        />
      )}
    </Field>
  )
})

type SelectProps = SelectHTMLAttributes<HTMLSelectElement> & { label: string; error?: string; hint?: string; children: ReactNode }

export const SelectInput = forwardRef<HTMLSelectElement, SelectProps>(function SelectInput({ label, error, hint, required, className, children, ...props }, ref) {
  return (
    <Field label={label} error={error} hint={hint} required={required} className={className}>
      {(id, describedBy) => (
        <select ref={ref} id={id} aria-invalid={Boolean(error)} aria-describedby={describedBy} className={cn(CONTROL, error && 'ring-red-500')} {...props}>
          {children}
        </select>
      )}
    </Field>
  )
})

type TextareaProps = TextareaHTMLAttributes<HTMLTextAreaElement> & { label: string; error?: string; hint?: string }

export const TextArea = forwardRef<HTMLTextAreaElement, TextareaProps>(function TextArea({ label, error, hint, required, className, ...props }, ref) {
  return (
    <Field label={label} error={error} hint={hint} required={required} className={className}>
      {(id, describedBy) => (
        <textarea ref={ref} id={id} rows={3} aria-invalid={Boolean(error)} aria-describedby={describedBy} className={cn(CONTROL, error && 'ring-red-500')} {...props} />
      )}
    </Field>
  )
})

export const Checkbox = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement> & { label: string; description?: string }>(
  function Checkbox({ label, description, className, ...props }, ref) {
    const id = useId()
    return (
      <div className={cn('flex items-start gap-3', className)}>
        <input ref={ref} id={id} type="checkbox" className="mt-0.5 size-4 rounded border-slate-300 text-brand-700 focus:ring-brand-600" {...props} />
        <label htmlFor={id} className="text-sm">
          <span className="font-medium text-slate-800">{label}</span>
          {description && <span className="block text-slate-500">{description}</span>}
        </label>
      </div>
    )
  },
)
