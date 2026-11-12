import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { describe, expect, it } from 'vitest'
import { TextInput } from '../components/ui/Field'
import { Modal } from '../components/ui/Modal'
import '../i18n'

function Form() {
  const [name, setName] = useState('')
  const [password, setPassword] = useState('')
  // A fresh onClose every render, like the real dialogs pass.
  const close = () => {}
  return (
    <Modal open title="Add user" onClose={close}>
      <TextInput label="Name" value={name} onChange={(e) => setName(e.target.value)} />
      <TextInput label="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
    </Modal>
  )
}

describe('Modal typing', () => {
  it('keeps focus in the password box while typing', async () => {
    const user = userEvent.setup()
    render(<Form />)
    const password = screen.getByLabelText('Password')
    await user.click(password)
    await user.keyboard('Secret-123')
    expect(password).toHaveValue('Secret-123')
    expect(password).toHaveFocus()
    expect(screen.getByLabelText('Name')).toHaveValue('')
  })

  it('shows and hides the password with the eye button', async () => {
    const user = userEvent.setup()
    render(<Form />)
    const password = screen.getByLabelText('Password')
    expect(password).toHaveAttribute('type', 'password')
    await user.click(screen.getByRole('button', { name: 'Show password' }))
    expect(password).toHaveAttribute('type', 'text')
    await user.click(screen.getByRole('button', { name: 'Hide password' }))
    expect(password).toHaveAttribute('type', 'password')
  })
})
