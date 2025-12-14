import { useEffect, useRef, useCallback } from 'react';
import { EditorState } from '@codemirror/state';
import { EditorView, lineNumbers, placeholder as placeholderExt } from '@codemirror/view';
import { syntaxHighlighting, defaultHighlightStyle } from '@codemirror/language';
import { sql } from '@codemirror/lang-sql';
import styles from './CodeEditor.module.css';

interface CodeEditorProps {
  value: string;
  onChange?: (value: string) => void;
  language: 'sql' | 'plain';
  readOnly?: boolean;
  placeholder?: string;
  minHeight?: number;
}

export const CodeEditor = ({
  value,
  onChange,
  language,
  readOnly = false,
  placeholder = '',
  minHeight = 200,
}: CodeEditorProps) => {
  const editorRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef<EditorView | null>(null);

  // onChange をメモ化して再生成を防ぐ
  const onChangeRef = useRef(onChange);
  onChangeRef.current = onChange;

  const handleChange = useCallback((newValue: string) => {
    onChangeRef.current?.(newValue);
  }, []);

  useEffect(() => {
    if (!editorRef.current) return;

    // 既存のエディタがあれば破棄
    if (viewRef.current) {
      viewRef.current.destroy();
    }

    // 拡張機能を構築
    const extensions = [
      lineNumbers(),
      EditorView.lineWrapping,
      EditorView.theme({
        '&': {
          fontSize: '14px',
          border: '1px solid #d1d5db',
          borderRadius: '6px',
          backgroundColor: '#f9fafb', // 左側のガターと同じ背景色
        },
        '&.cm-focused': {
          outline: 'none',
          borderColor: '#3a4e72',
          boxShadow: '0 0 0 3px rgba(58, 78, 114, 0.1)',
        },
        '.cm-scroller': {
          overflow: 'auto',
          minHeight: `${minHeight}px`,
        },
        '.cm-content': {
          fontFamily: "'Fira Code', 'JetBrains Mono', 'Consolas', monospace",
          padding: '12px 0',
          minHeight: `${minHeight - 24}px`,
          backgroundColor: '#ffffff', // コンテンツエリアは白
        },
        '.cm-line': {
          padding: '0 12px',
        },
        '.cm-gutters': {
          backgroundColor: '#f9fafb',
          borderRight: '1px solid #e5e7eb',
          borderRadius: '6px 0 0 6px',
          color: '#9ca3af',
        },
        '.cm-activeLineGutter': {
          backgroundColor: '#f3f4f6',
        },
        '.cm-activeLine': {
          backgroundColor: 'rgba(58, 78, 114, 0.05)',
        },
        '.cm-placeholder': {
          color: '#9ca3af',
          fontStyle: 'italic',
        },
      }),
    ];

    // シンタックスハイライトのスタイルを追加
    extensions.push(syntaxHighlighting(defaultHighlightStyle, { fallback: true }));

    // 言語拡張を追加
    if (language === 'sql') {
      extensions.push(sql());
    }

    // プレースホルダーを追加
    if (placeholder) {
      extensions.push(placeholderExt(placeholder));
    }

    // 読み取り専用設定
    if (readOnly) {
      extensions.push(EditorState.readOnly.of(true));
      extensions.push(EditorView.editable.of(false));
    } else {
      // 変更リスナーを追加（編集可能な場合のみ）
      extensions.push(
        EditorView.updateListener.of((update) => {
          if (update.docChanged) {
            handleChange(update.state.doc.toString());
          }
        }),
      );
    }

    // エディタを作成
    const state = EditorState.create({
      doc: value,
      extensions,
    });

    const view = new EditorView({
      state,
      parent: editorRef.current,
    });

    viewRef.current = view;

    return () => {
      view.destroy();
    };
    // language, readOnly, placeholder, minHeight が変わった時だけ再生成
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [language, readOnly, placeholder, minHeight]);

  // 外部からの value 変更を反映（エディタ内容と異なる場合のみ）
  useEffect(() => {
    const view = viewRef.current;
    if (!view) return;

    const currentValue = view.state.doc.toString();
    if (currentValue !== value) {
      view.dispatch({
        changes: {
          from: 0,
          to: currentValue.length,
          insert: value,
        },
      });
    }
  }, [value]);

  return <div ref={editorRef} className={`${styles.editor} ${readOnly ? styles.readOnly : ''}`} />;
};
