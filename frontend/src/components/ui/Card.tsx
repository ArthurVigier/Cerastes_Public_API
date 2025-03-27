import React from 'react';

interface CardProps {
  title?: string;
  children: React.ReactNode;
  className?: string;
  footer?: React.ReactNode;
}

export default function Card({ title, children, className = '', footer }: CardProps) {
  return (
    <div className={`card ${className}`}>
      {title && <h2 className="text-xl font-semibold mb-4">{title}</h2>}
      <div>{children}</div>
      {footer && <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">{footer}</div>}
    </div>
  );
}