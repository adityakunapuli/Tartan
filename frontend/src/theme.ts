import { createTheme, type MantineColorsTuple } from '@mantine/core'

const brandColor: MantineColorsTuple = [
  '#eef3ff', '#dce4fd', '#b9c9fc', '#8ba8fa',
  '#5b82f5', '#3a66f2', '#244ee8', '#1d3ed0',
  '#1a34ab', '#172e89',
]

export const theme = createTheme({
  primaryColor: 'brand',
  colors: {
    brand: brandColor,
    dark: [
      '#e4e4ed',
      '#b0b0bf',
      '#7a7a8f',
      '#50506b',
      '#35354d',
      '#26263c',
      '#1c1c2e',
      '#141421',
      '#0d0d18',
      '#070710',
    ],
  },
  fontFamily: 'system-ui, -apple-system, sans-serif',
  defaultRadius: 'sm',
  components: {
    Paper: {
      defaultProps: {
        withBorder: true,
      },
      styles: {
        root: {
          borderColor: 'var(--mantine-color-dark-4)',
        },
      },
    },
    Table: {
      defaultProps: {
        highlightOnHover: true,
      },
    },
    Badge: {
      defaultProps: {
        variant: 'light',
        size: 'sm',
      },
    },
    TextInput: {
      defaultProps: {
        size: 'xs',
      },
    },
    Select: {
      defaultProps: {
        size: 'xs',
      },
    },
    AppShell: {
      styles: {
        main: {
          backgroundColor: 'var(--mantine-color-dark-8)',
        },
      },
    },
    Card: {
      defaultProps: {
        withBorder: true,
      },
    },
  },
})