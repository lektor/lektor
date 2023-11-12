/**
 * Marshall objects to and from JSON strings.
 */

/* eslint-disable @typescript-eslint/no-explicit-any */
type TypeDescriptor<TypeConstructor extends new (arg: any) => any> = {
  type: TypeConstructor;
  validate: (value: any) => void;
};
/* eslint-enable */

type TypeDescriptorType<TypeDesc> = TypeDesc extends TypeDescriptor<infer C>
  ? InstanceType<C>
  : never;

export type MarshallPropMap = {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  [name: string]: TypeDescriptor<any>;
};

export type MarshallType<PropMap extends MarshallPropMap> = {
  [P in keyof PropMap]: TypeDescriptorType<PropMap[P]>;
};

/**
 * Convert object to/from (untrusted) JSON string.
 */
export class Marshall<PropMap extends MarshallPropMap> {
  readonly propMap: PropMap;

  constructor(propMap: PropMap) {
    this.propMap = propMap;
  }

  serialize(value: MarshallType<PropMap>) {
    // pick those properties listed in propMap and JSONify
    return JSON.stringify(
      Object.keys(this.propMap).reduce(
        (pick, name) => ({ ...pick, [name]: value[name] }),
        {},
      ),
    );
  }

  /**
   * Deserialize saved state.
   *
   * Note that this may throw various exceptions if deserialization fails.
   */
  deserialize(serialized: string | null | undefined): MarshallType<PropMap> {
    /* eslint-disable
       @typescript-eslint/no-unsafe-assignment,
       @typescript-eslint/no-unsafe-member-access */
    const data = JSON.parse(serialized ?? "");
    const value = {} as MarshallType<PropMap>;
    for (const prop in this.propMap) {
      const { validate } = this.propMap[prop];
      validate(data[prop]);
      value[prop] = data[prop];
    }
    return value;
    /* eslint-enable */
  }
}

export const marshallTypes = {
  boolean: {
    type: Boolean,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    validate(v: any): asserts v is boolean {
      if (typeof v !== "boolean") {
        throw new Error(`${v} is not an boolean`);
      }
    },
  },

  number: {
    type: Number,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    validate(v: any): asserts v is number {
      if (typeof v !== "number" || isNaN(v)) {
        throw new Error(`${v} is not an number`);
      }
    },
  },
};
