import Quill, { DeltaStatic } from "quill";

export interface QuillGraphDataConfig {
  container: string
}

export default class QuillGraphData {
  private _quill: Quill;
  private _options: QuillGraphDataConfig;
  private _quillSelector: HTMLSpanElement;
  private _list: HTMLSelectElement;

  constructor(quill, options) {
    this._quill = quill;
    this._options = options;

    const contianer = document.querySelector(this._options.container);
    const button = contianer.querySelector('button');
    this._list = contianer.querySelector('select');
    this._quillSelector = contianer.querySelector('.quill-custom-select > .ql-picker-label') as HTMLSpanElement;
    this.updateCaption();
    button.addEventListener('click', (e) => {
      console.log(this._list.value);
      var selection = this._quill.getSelection(true);
      if (selection.length > 0)
        this._quill.deleteText(selection.index, selection.length);
      var delta: DeltaStatic = this._quill.insertEmbed(selection.index, 'graphdata', `${this._list.value}`, 'user');
      this._quill.insertText(selection.index + 1, ' ', "user");
      this._quill.updateContents(delta, 'user');
      this._quill.focus();
      console.log(delta);
    });
    this._list.addEventListener('change', (e) => {
      this.updateCaption();
    })
  }

  updateCaption() {
    var caption = (this._list.querySelector('option[value="' + this._list.value + '"]') as HTMLOptionElement).innerText;
    if (this._quillSelector.childNodes.item(0).nodeType !== 3)
        this._quillSelector.prepend(caption);
      else
        this._quillSelector.childNodes.item(0).textContent = caption;
  }

  reloadList(items: string[][]) {
    const contianer = document.querySelector(this._options.container);
    var list = contianer.querySelector('.quill-custom-select');
    var select = list.querySelector(".ql-picker-options");
    select.innerHTML = "";
    var selection = list.querySelector(".ql-picker-label") as HTMLSpanElement;
    var f = document.createDocumentFragment();
    for (let item of items) {
      var span = document.createElement("span");
      span.tabIndex = 0;
      span.setAttribute("role", "button");
      span.classList.add("ql-picker-item");
      if (f.children.length === 0)
        span.classList.add("ql-selected");
      span.setAttribute("data-value", item[0]);
      span.setAttribute("data-label", item[1]);
      span.addEventListener("click", function(e) {
        var spans = select.querySelectorAll("span");
        var index = -1;
        spans.forEach((s, i) => {
          s.classList.remove("ql-selected");
          if (s.getAttribute("data-value") === this.getAttribute("data-value"))
            index = i;
        });
        this.classList.add("ql-selected");
        list.classList.remove("ql-expanded");
        selection.setAttribute("data-value", this.getAttribute("data-value"));
        selection.setAttribute("data-label", this.getAttribute("data-label"));
        selection.childNodes[0].nodeValue = this.getAttribute("data-label");
        var htmlSelect = contianer.querySelector("select") as HTMLSelectElement;
        htmlSelect.selectedIndex = index;
      });
      f.append(span);
    }
    select.append(f);
  }
}


let Inline = Quill.import('blots/inline');

export class GraphDataBlot extends Inline {

  static create(value) {
    console.log("create");
    console.log(value);
    let node = super.create(value);
    node.setAttribute('contenteditable', 'false');
    node.setAttribute('spellcheck', 'false');
    var nextId = 0;
    document.querySelectorAll('.graphdata').forEach((b) => {
      var id = parseInt(b.id);
      if (nextId < id)
        nextId = id;
    });
    nextId++;

    node.setAttribute('id', nextId.toString());
    if (value !== GraphDataBlot.blotName) {
      (node as HTMLSpanElement).innerText = `{{${value}}}`;
    }
    node.addEventListener('mousedown', function(e) {
      let blot = Quill.find(node) as GraphDataBlot;
      console.log(blot);
      let range = document.createRange();
      range.selectNodeContents(blot.domNode);
      console.log(range);
      var sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(range);
    });
    node.addEventListener('keydown', function(e) {
      if (e.keyCode === "13") {
        e.preventDefault();
        e.stopPropagation();
      }
    });
    console.log(node);
    return node;
  }

  static formats(domNode: HTMLSpanElement) {
    console.log("formats");
    console.log(domNode);
    if (domNode.children.length > 0) {
      let child: HTMLElement = domNode.children.item(0) as HTMLElement;
      child.classList.forEach((name) => {
        if (name.startsWith('ql-color-'))
        child.style.color = name.replace('ql-color-', '');
      else if (name.startsWith('ql-bg-'))
        child.style.backgroundColor = name.replace('ql-bg-', '');
      else if (name.startsWith('ql-size-')) {
        let value = name.replace('ql-size-', '');
        child.style.fontSize = value === 'small' ? 'smaller' : value;
      }
      })
    }
    return domNode.getAttribute("class");
  }

  format(name, value: string) {
    console.log("format");
    console.log(name, value)
    var span = this.domNode as HTMLSpanElement;
    if (name !== this.statics.blotName || !value) {
      super.format(name, value);
    }
    if (value) {
      if (name === 'color')
        span.style.color = value;
      else if (name === 'background')
        span.style.backgroundColor = value;
      else if (name === 'size') {
        span.style.fontSize = value === 'small' ? 'smaller' : value;
        span.classList.remove(...['ql-size-normal', 'ql-size-small', 'ql-size-large']);
        span.classList.add(`ql-size-${value}`);
      }
    }
  }

  optimize(context: any) {
    // Never optimize/merge these
  }

  insertAt(index: number, embed: string, value: any) {
    console.log(index);
    console.log(embed);
    console.log(value);
  }
}
GraphDataBlot.blotName = 'graphdata';
GraphDataBlot.tagName = 'SPAN';
GraphDataBlot.className = 'graphdata';
Quill.register(GraphDataBlot);

var BackgroundClass = Quill.import('attributors/class/background');
var ColorClass = Quill.import('attributors/class/color');
var SizeStyle = Quill.import('attributors/style/size');
Quill.register(BackgroundClass, true);
Quill.register(ColorClass, true);
Quill.register(SizeStyle, true);
