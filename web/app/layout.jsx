import "./globals.css";

export const metadata = {
  title: "Recupera",
  description: "Facturas pagables y pagadas a tiempo para pymes",
};

export default function RootLayout({ children }) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}

